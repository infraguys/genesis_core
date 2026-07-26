// Copyright 2026 Genesis Corporation
//
// All Rights Reserved.
//
//    Licensed under the Apache License, Version 2.0 (the "License"); you may
//    not use this file except in compliance with the License. You may obtain
//    a copy of the License at
//
//         http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
//    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
//    License for the specific language governing permissions and limitations
//    under the License.

package app

import (
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

const (
	iamRoutePrefix       = "/v1/iam/clients/"
	invalidationPrefix   = "/internal/v1/cache/introspection/"
	maxUpstreamBodyBytes = 4 << 20
)

var hopByHopHeaders = map[string]struct{}{
	"Connection":          {},
	"Keep-Alive":          {},
	"Proxy-Authenticate":  {},
	"Proxy-Authorization": {},
	"Te":                  {},
	"Trailer":             {},
	"Transfer-Encoding":   {},
	"Upgrade":             {},
}

// Proxy serves the public caching API and the internal invalidation API.
type Proxy struct {
	coreURL            *url.URL
	client             *http.Client
	introspectionCache *introspectionCache
	jwksCache          *jwksCache
	introspectionCalls *flightGroup
	jwksCalls          *flightGroup
}

// NewProxy constructs a proxy from validated configuration.
func NewProxy(config Config) *Proxy {
	return &Proxy{
		coreURL: config.CoreURL,
		client: &http.Client{
			Timeout: config.RequestTimeout,
			CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
		introspectionCache: newIntrospectionCache(
			config.IntrospectionCacheTTL,
			config.IntrospectionCacheMaxEntries,
		),
		jwksCache: newJWKSCache(
			config.JWKSCacheTTL,
			config.JWKSCacheMaxEntries,
		),
		introspectionCalls: newFlightGroup(),
		jwksCalls:          newFlightGroup(),
	}
}

// PublicHandler returns the handler for consumers of the cached IAM API.
func (proxy *Proxy) PublicHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health/live", healthHandler)
	mux.HandleFunc("/health/ready", healthHandler)
	mux.HandleFunc(iamRoutePrefix, proxy.handleIAM)
	return mux
}

// InternalHandler returns the handler intended only for Core.
func (proxy *Proxy) InternalHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health/live", healthHandler)
	mux.HandleFunc(invalidationPrefix, proxy.handleInvalidation)
	return mux
}

func healthHandler(response http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodGet {
		response.Header().Set("Allow", http.MethodGet)
		http.Error(response, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(http.StatusOK)
	_, _ = response.Write([]byte(`{"status":"ok"}`))
}

func (proxy *Proxy) handleIAM(response http.ResponseWriter, request *http.Request) {
	clientUUID, action, cacheableRoute := parseIAMRoute(request.URL.Path)
	if request.Method != http.MethodGet ||
		!cacheableRoute ||
		hasHeader(request.Header, "X-OTP") {
		proxy.forward(response, request)
		return
	}

	switch action {
	case "introspect":
		proxy.handleIntrospection(response, request, clientUUID)
	case "jwks":
		proxy.handleJWKS(response, request, clientUUID)
	}
}

func parseIAMRoute(path string) (string, string, bool) {
	if !strings.HasPrefix(path, iamRoutePrefix) {
		return "", "", false
	}
	parts := strings.Split(strings.TrimPrefix(path, iamRoutePrefix), "/")
	if len(parts) != 3 || parts[0] == "" || parts[1] != "actions" {
		return "", "", false
	}
	if parts[2] != "introspect" && parts[2] != "jwks" {
		return "", "", false
	}
	return parts[0], parts[2], true
}

func (proxy *Proxy) handleIntrospection(
	writer http.ResponseWriter,
	request *http.Request,
	clientUUID string,
) {
	accessToken, hasBearer := bearerToken(request.Header.Get("Authorization"))
	if !hasBearer {
		proxy.forward(writer, request)
		return
	}

	if response, ok := proxy.introspectionCache.get(accessToken, clientUUID); ok {
		writeCachedResponse(writer, response)
		return
	}

	claims, claimsOK := parseAccessTokenClaims(accessToken)
	flightKey := "introspection:" + clientUUID + ":" + tokenKeyString(accessToken)
	upstreamResponse, err := proxy.introspectionCalls.do(
		request.Context(),
		flightKey,
		func() (cachedResponse, error) {
			if response, ok := proxy.introspectionCache.get(
				accessToken,
				clientUUID,
			); ok {
				return response, nil
			}

			epoch := proxy.introspectionCache.currentEpoch()
			response, err := proxy.fetchUpstream(request)
			if err != nil {
				return cachedResponse{}, err
			}
			if response.statusCode == http.StatusOK && claimsOK {
				proxy.introspectionCache.put(
					accessToken,
					claims.TokenUUID,
					clientUUID,
					claims.ExpiresAt,
					response,
					epoch,
				)
			}
			return response, nil
		},
	)
	if err != nil {
		writeUpstreamError(writer, err)
		return
	}
	writeCachedResponse(writer, upstreamResponse)
}

func (proxy *Proxy) handleJWKS(
	writer http.ResponseWriter,
	request *http.Request,
	clientUUID string,
) {
	if response, ok := proxy.jwksCache.get(clientUUID); ok {
		writeCachedResponse(writer, response)
		return
	}

	upstreamResponse, err := proxy.jwksCalls.do(
		request.Context(),
		"jwks:"+clientUUID,
		func() (cachedResponse, error) {
			if response, ok := proxy.jwksCache.get(clientUUID); ok {
				return response, nil
			}

			response, err := proxy.fetchUpstream(request)
			if err != nil {
				return cachedResponse{}, err
			}
			if response.statusCode == http.StatusOK {
				proxy.jwksCache.put(clientUUID, response)
			}
			return response, nil
		},
	)
	if err != nil {
		writeUpstreamError(writer, err)
		return
	}
	writeCachedResponse(writer, upstreamResponse)
}

func (proxy *Proxy) forward(writer http.ResponseWriter, request *http.Request) {
	upstreamRequest, err := proxy.newUpstreamRequest(request, request.Body)
	if err != nil {
		writeUpstreamError(writer, err)
		return
	}

	upstreamResponse, err := proxy.client.Do(upstreamRequest)
	if err != nil {
		writeUpstreamError(writer, fmt.Errorf("request Core: %w", err))
		return
	}
	defer upstreamResponse.Body.Close()

	copyEndToEndHeaders(writer.Header(), upstreamResponse.Header)
	writer.WriteHeader(upstreamResponse.StatusCode)
	if _, err := io.Copy(writer, upstreamResponse.Body); err != nil {
		log.Printf("stream IAM upstream response: %v", err)
	}
}

func (proxy *Proxy) fetchUpstream(request *http.Request) (cachedResponse, error) {
	upstreamRequest, err := proxy.newUpstreamRequest(request, nil)
	if err != nil {
		return cachedResponse{}, err
	}

	upstreamResponse, err := proxy.client.Do(upstreamRequest)
	if err != nil {
		return cachedResponse{}, fmt.Errorf("request Core: %w", err)
	}
	defer upstreamResponse.Body.Close()

	body, err := io.ReadAll(io.LimitReader(
		upstreamResponse.Body,
		maxUpstreamBodyBytes+1,
	))
	if err != nil {
		return cachedResponse{}, fmt.Errorf("read Core response: %w", err)
	}
	if len(body) > maxUpstreamBodyBytes {
		return cachedResponse{}, errors.New("Core response exceeds size limit")
	}

	return cachedResponse{
		statusCode: upstreamResponse.StatusCode,
		header:     sanitizedHeaders(upstreamResponse.Header),
		body:       body,
	}, nil
}

func (proxy *Proxy) newUpstreamRequest(
	request *http.Request,
	body io.Reader,
) (*http.Request, error) {
	upstreamURL := strings.TrimRight(proxy.coreURL.String(), "/") +
		request.URL.EscapedPath()
	if request.URL.RawQuery != "" {
		upstreamURL += "?" + request.URL.RawQuery
	}

	upstreamRequest, err := http.NewRequestWithContext(
		request.Context(),
		request.Method,
		upstreamURL,
		body,
	)
	if err != nil {
		return nil, fmt.Errorf("build upstream request: %w", err)
	}
	copyEndToEndHeaders(upstreamRequest.Header, request.Header)
	upstreamRequest.Host = request.Host
	if body != nil {
		upstreamRequest.ContentLength = request.ContentLength
		upstreamRequest.TransferEncoding = append(
			[]string(nil),
			request.TransferEncoding...,
		)
	}

	return upstreamRequest, nil
}

func copyEndToEndHeaders(destination, source http.Header) {
	for name, values := range source {
		if _, skip := hopByHopHeaders[http.CanonicalHeaderKey(name)]; skip {
			continue
		}
		for _, value := range values {
			destination.Add(name, value)
		}
	}
}

func sanitizedHeaders(source http.Header) http.Header {
	result := make(http.Header)
	copyEndToEndHeaders(result, source)
	result.Del("Content-Length")
	return result
}

func writeCachedResponse(writer http.ResponseWriter, response cachedResponse) {
	copyEndToEndHeaders(writer.Header(), response.header)
	writer.WriteHeader(response.statusCode)
	_, _ = writer.Write(response.body)
}

func writeUpstreamError(writer http.ResponseWriter, err error) {
	log.Printf("IAM upstream request failed: %v", err)
	http.Error(writer, "IAM upstream unavailable", http.StatusBadGateway)
}

func bearerToken(value string) (string, bool) {
	parts := strings.Fields(value)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
		return "", false
	}
	return parts[1], true
}

func hasHeader(header http.Header, name string) bool {
	for key := range header {
		if strings.EqualFold(key, name) {
			return true
		}
	}
	return false
}

type accessTokenClaims struct {
	TokenUUID string
	ExpiresAt time.Time
}

func parseAccessTokenClaims(accessToken string) (accessTokenClaims, bool) {
	parts := strings.Split(accessToken, ".")
	if len(parts) != 3 {
		return accessTokenClaims{}, false
	}

	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return accessTokenClaims{}, false
	}
	var claims struct {
		JTI string          `json:"jti"`
		Exp json.RawMessage `json:"exp"`
	}
	if err := json.Unmarshal(payload, &claims); err != nil || claims.JTI == "" {
		return accessTokenClaims{}, false
	}

	expiration, err := strconv.ParseInt(string(claims.Exp), 10, 64)
	if err != nil {
		return accessTokenClaims{}, false
	}
	return accessTokenClaims{
		TokenUUID: claims.JTI,
		ExpiresAt: time.Unix(expiration, 0),
	}, true
}

func tokenKeyString(accessToken string) string {
	key := makeAccessTokenKey(accessToken)
	return hex.EncodeToString(key[:])
}

func (proxy *Proxy) handleInvalidation(
	writer http.ResponseWriter,
	request *http.Request,
) {
	if request.Method != http.MethodDelete {
		writer.Header().Set("Allow", http.MethodDelete)
		http.Error(writer, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	tokenUUID := strings.TrimPrefix(request.URL.Path, invalidationPrefix)
	if strings.Contains(tokenUUID, "/") {
		http.NotFound(writer, request)
		return
	}
	if !validUUID(tokenUUID) {
		http.Error(writer, "invalid token UUID", http.StatusBadRequest)
		return
	}

	proxy.introspectionCache.invalidate(tokenUUID)
	writer.WriteHeader(http.StatusNoContent)
}

func validUUID(value string) bool {
	if len(value) != 36 {
		return false
	}
	for index, char := range value {
		switch index {
		case 8, 13, 18, 23:
			if char != '-' {
				return false
			}
		default:
			if !strings.ContainsRune("0123456789abcdefABCDEF", char) {
				return false
			}
		}
	}
	return true
}
