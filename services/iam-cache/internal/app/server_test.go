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
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

const testTokenUUID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

func TestIntrospectionCachesSuccessfulResponse(t *testing.T) {
	t.Parallel()

	token := testAccessToken(testTokenUUID, time.Now().Add(time.Hour))
	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		request *http.Request,
	) {
		calls.Add(1)
		if got, want := request.URL.Path, "/api/core/v1/iam/clients/client-one/actions/introspect"; got != want {
			t.Errorf("upstream path = %q, want %q", got, want)
		}
		if got, want := request.Header.Get("Authorization"), "Bearer "+token; got != want {
			t.Errorf("Authorization header = %q, want %q", got, want)
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{"permissions":["read"]}`))
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL+"/api/core", time.Minute, time.Minute)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	for range 2 {
		response := makePublicRequest(
			t,
			server.URL+"/v1/iam/clients/client-one/actions/introspect",
			token,
			"",
		)
		assertResponse(t, response, http.StatusOK, `{"permissions":["read"]}`)
	}

	if got, want := calls.Load(), int32(1); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
}

func TestXOTPAlwaysBypassesIntrospectionCache(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	var receivedOTP []string
	var mu sync.Mutex
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		request *http.Request,
	) {
		call := calls.Add(1)
		mu.Lock()
		receivedOTP = append(receivedOTP, request.Header.Get("X-OTP"))
		mu.Unlock()
		writer.Header().Set("Content-Type", "application/json")
		_, _ = fmt.Fprintf(writer, `{"call":%d}`, call)
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, time.Minute, time.Minute)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	token := testAccessToken(testTokenUUID, time.Now().Add(time.Hour))
	for _, otp := range []string{"111111", "222222"} {
		response := makePublicRequest(
			t,
			server.URL+"/v1/iam/clients/client-one/actions/introspect",
			token,
			otp,
		)
		assertResponse(t, response, http.StatusOK, "")
	}
	response := makePublicRequest(
		t,
		server.URL+"/v1/iam/clients/client-one/actions/introspect",
		token,
		"",
	)
	assertResponse(t, response, http.StatusOK, `{"call":3}`)
	response = makePublicRequest(
		t,
		server.URL+"/v1/iam/clients/client-one/actions/introspect",
		token,
		"",
	)
	assertResponse(t, response, http.StatusOK, `{"call":3}`)

	if got, want := calls.Load(), int32(3); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
	mu.Lock()
	defer mu.Unlock()
	if got, want := strings.Join(receivedOTP, ","), "111111,222222,"; got != want {
		t.Fatalf("received OTP values = %q, want %q", got, want)
	}
}

func TestXOTPAlwaysBypassesJWKSCache(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		request *http.Request,
	) {
		call := calls.Add(1)
		if got, want := request.Header.Get("X-OTP"), "123456"; got != want {
			t.Errorf("X-OTP = %q, want %q", got, want)
		}
		_, _ = fmt.Fprintf(writer, `{"call":%d}`, call)
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, time.Hour, time.Hour)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	endpoint := server.URL + "/v1/iam/clients/client-one/actions/jwks"
	for call := 1; call <= 2; call++ {
		request, err := http.NewRequest(http.MethodGet, endpoint, nil)
		if err != nil {
			t.Fatalf("create JWKS request: %v", err)
		}
		request.Header.Set("X-OTP", "123456")

		response, err := http.DefaultClient.Do(request)
		if err != nil {
			t.Fatalf("perform JWKS request: %v", err)
		}
		assertResponse(
			t,
			response,
			http.StatusOK,
			fmt.Sprintf(`{"call":%d}`, call),
		)
	}

	if got, want := calls.Load(), int32(2); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
}

func TestTokenRequestPassesThroughWithoutCaching(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		request *http.Request,
	) {
		call := calls.Add(1)
		if got, want := request.Method, http.MethodPost; got != want {
			t.Errorf("method = %q, want %q", got, want)
		}
		if got, want := request.URL.Path, "/api/core/v1/iam/clients/client-one/actions/get_token/invoke"; got != want {
			t.Errorf("upstream path = %q, want %q", got, want)
		}
		if got, want := request.URL.RawQuery, "source=test"; got != want {
			t.Errorf("query = %q, want %q", got, want)
		}
		if got, want := request.Header.Get("X-OTP"), "123456"; got != want {
			t.Errorf("X-OTP = %q, want %q", got, want)
		}
		body, err := io.ReadAll(request.Body)
		if err != nil {
			t.Errorf("read request body: %v", err)
		}
		if got, want := string(body), "grant_type=password"; got != want {
			t.Errorf("body = %q, want %q", got, want)
		}
		writer.Header().Set("X-Upstream-Call", fmt.Sprint(call))
		writer.WriteHeader(http.StatusCreated)
		_, _ = writer.Write([]byte(`{"access_token":"token"}`))
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL+"/api/core", time.Hour, time.Hour)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	endpoint := server.URL +
		"/v1/iam/clients/client-one/actions/get_token/invoke?source=test"
	for range 2 {
		request, err := http.NewRequest(
			http.MethodPost,
			endpoint,
			strings.NewReader("grant_type=password"),
		)
		if err != nil {
			t.Fatalf("create token request: %v", err)
		}
		request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		request.Header.Set("X-OTP", "123456")

		response, err := http.DefaultClient.Do(request)
		if err != nil {
			t.Fatalf("perform token request: %v", err)
		}
		assertResponse(
			t,
			response,
			http.StatusCreated,
			`{"access_token":"token"}`,
		)
	}

	if got, want := calls.Load(), int32(2); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
}

func TestIntrospectionCacheExpires(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		_ *http.Request,
	) {
		call := calls.Add(1)
		_, _ = fmt.Fprintf(writer, `{"call":%d}`, call)
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, 20*time.Millisecond, time.Minute)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	token := testAccessToken(testTokenUUID, time.Now().Add(time.Hour))
	first := makePublicRequest(
		t,
		server.URL+"/v1/iam/clients/client-one/actions/introspect",
		token,
		"",
	)
	assertResponse(t, first, http.StatusOK, `{"call":1}`)
	time.Sleep(30 * time.Millisecond)
	second := makePublicRequest(
		t,
		server.URL+"/v1/iam/clients/client-one/actions/introspect",
		token,
		"",
	)
	assertResponse(t, second, http.StatusOK, `{"call":2}`)
}

func TestJWKSUsesIndependentCache(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		request *http.Request,
	) {
		if !strings.HasSuffix(request.URL.Path, "/actions/jwks") {
			http.NotFound(writer, request)
			return
		}
		call := calls.Add(1)
		_, _ = fmt.Fprintf(writer, `{"keys":[{"call":%d}]}`, call)
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, time.Hour, 20*time.Millisecond)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	endpoint := server.URL + "/v1/iam/clients/client-one/actions/jwks"
	first := makePublicRequest(t, endpoint, "", "")
	assertResponse(t, first, http.StatusOK, `{"keys":[{"call":1}]}`)
	second := makePublicRequest(t, endpoint, "", "")
	assertResponse(t, second, http.StatusOK, `{"keys":[{"call":1}]}`)
	time.Sleep(30 * time.Millisecond)
	third := makePublicRequest(t, endpoint, "", "")
	assertResponse(t, third, http.StatusOK, `{"keys":[{"call":2}]}`)
}

func TestInternalInvalidationRemovesAllAccessTokens(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		_ *http.Request,
	) {
		call := calls.Add(1)
		_, _ = fmt.Fprintf(writer, `{"call":%d}`, call)
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, time.Hour, time.Hour)
	publicServer := httptest.NewServer(proxy.PublicHandler())
	defer publicServer.Close()
	internalServer := httptest.NewServer(proxy.InternalHandler())
	defer internalServer.Close()

	tokens := []string{
		testAccessToken(testTokenUUID, time.Now().Add(time.Hour)),
		testAccessTokenWithNonce(testTokenUUID, time.Now().Add(time.Hour), "second"),
	}
	for _, token := range tokens {
		response := makePublicRequest(
			t,
			publicServer.URL+"/v1/iam/clients/client-one/actions/introspect",
			token,
			"",
		)
		assertResponse(t, response, http.StatusOK, "")
	}

	request, err := http.NewRequest(
		http.MethodDelete,
		internalServer.URL+invalidationPrefix+testTokenUUID,
		nil,
	)
	if err != nil {
		t.Fatalf("create invalidation request: %v", err)
	}
	invalidationResponse, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatalf("perform invalidation request: %v", err)
	}
	assertResponse(t, invalidationResponse, http.StatusNoContent, "")

	for _, token := range tokens {
		response := makePublicRequest(
			t,
			publicServer.URL+"/v1/iam/clients/client-one/actions/introspect",
			token,
			"",
		)
		assertResponse(t, response, http.StatusOK, "")
	}

	if got, want := calls.Load(), int32(4); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
}

func TestUpstreamErrorsAreNotCached(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		_ *http.Request,
	) {
		calls.Add(1)
		http.Error(writer, "denied", http.StatusUnauthorized)
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, time.Hour, time.Hour)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()

	token := testAccessToken(testTokenUUID, time.Now().Add(time.Hour))
	for range 2 {
		response := makePublicRequest(
			t,
			server.URL+"/v1/iam/clients/client-one/actions/introspect",
			token,
			"",
		)
		assertResponse(t, response, http.StatusUnauthorized, "")
	}
	if got, want := calls.Load(), int32(2); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
}

func TestConcurrentMissesAreCoalesced(t *testing.T) {
	t.Parallel()

	var calls atomic.Int32
	release := make(chan struct{})
	upstream := httptest.NewServer(http.HandlerFunc(func(
		writer http.ResponseWriter,
		_ *http.Request,
	) {
		calls.Add(1)
		<-release
		_, _ = writer.Write([]byte(`{"permissions":[]}`))
	}))
	defer upstream.Close()

	proxy := newTestProxy(t, upstream.URL, time.Hour, time.Hour)
	server := httptest.NewServer(proxy.PublicHandler())
	defer server.Close()
	token := testAccessToken(testTokenUUID, time.Now().Add(time.Hour))

	const requests = 8
	results := make(chan int, requests)
	for range requests {
		go func() {
			response := makePublicRequest(
				t,
				server.URL+"/v1/iam/clients/client-one/actions/introspect",
				token,
				"",
			)
			results <- response.StatusCode
			_, _ = io.Copy(io.Discard, response.Body)
			_ = response.Body.Close()
		}()
	}

	deadline := time.Now().Add(time.Second)
	for calls.Load() == 0 && time.Now().Before(deadline) {
		time.Sleep(time.Millisecond)
	}
	close(release)
	for range requests {
		if status := <-results; status != http.StatusOK {
			t.Errorf("status = %d, want %d", status, http.StatusOK)
		}
	}
	if got, want := calls.Load(), int32(1); got != want {
		t.Fatalf("upstream calls = %d, want %d", got, want)
	}
}

func newTestProxy(
	t *testing.T,
	coreURL string,
	introspectionTTL time.Duration,
	jwksTTL time.Duration,
) *Proxy {
	t.Helper()

	parsedURL, err := url.Parse(coreURL)
	if err != nil {
		t.Fatalf("parse Core URL: %v", err)
	}
	return NewProxy(Config{
		CoreURL:                      parsedURL,
		RequestTimeout:               time.Second,
		IntrospectionCacheTTL:        introspectionTTL,
		IntrospectionCacheMaxEntries: 100,
		JWKSCacheTTL:                 jwksTTL,
		JWKSCacheMaxEntries:          100,
	})
}

func makePublicRequest(
	t *testing.T,
	endpoint string,
	accessToken string,
	otp string,
) *http.Response {
	t.Helper()

	request, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err != nil {
		t.Fatalf("create request: %v", err)
	}
	if accessToken != "" {
		request.Header.Set("Authorization", "Bearer "+accessToken)
	}
	if otp != "" {
		request.Header.Set("X-OTP", otp)
	}
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		t.Fatalf("perform request: %v", err)
	}
	return response
}

func assertResponse(
	t *testing.T,
	response *http.Response,
	wantStatus int,
	wantBody string,
) {
	t.Helper()
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)
	if err != nil {
		t.Fatalf("read response: %v", err)
	}
	if got := response.StatusCode; got != wantStatus {
		t.Fatalf("status = %d, want %d; body = %q", got, wantStatus, body)
	}
	if wantBody != "" && strings.TrimSpace(string(body)) != wantBody {
		t.Fatalf("body = %q, want %q", body, wantBody)
	}
}

func testAccessToken(tokenUUID string, expiration time.Time) string {
	return testAccessTokenWithNonce(tokenUUID, expiration, "")
}

func testAccessTokenWithNonce(
	tokenUUID string,
	expiration time.Time,
	nonce string,
) string {
	header, _ := json.Marshal(map[string]string{"alg": "none"})
	payload, _ := json.Marshal(map[string]any{
		"jti":   tokenUUID,
		"exp":   expiration.Unix(),
		"nonce": nonce,
	})
	return base64.RawURLEncoding.EncodeToString(header) + "." +
		base64.RawURLEncoding.EncodeToString(payload) + ".signature"
}
