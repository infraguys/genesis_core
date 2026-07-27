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
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"
	"time"
)

const (
	defaultPublicListenAddress       = "127.0.0.1:11110"
	defaultInternalListenAddress     = "127.0.0.1:11111"
	defaultRequestTimeout            = 5 * time.Second
	defaultIntrospectionCacheTTL     = 15 * time.Second
	defaultIntrospectionCacheEntries = 100000
	defaultJWKSCacheTTL              = time.Minute
	defaultJWKSCacheEntries          = 1000
)

type fileConfig struct {
	PublicListenAddress          string `json:"public_listen_address"`
	InternalListenAddress        string `json:"internal_listen_address"`
	CoreURL                      string `json:"core_url"`
	RequestTimeout               string `json:"request_timeout"`
	IntrospectionCacheTTL        string `json:"introspection_cache_ttl"`
	IntrospectionCacheMaxEntries int    `json:"introspection_cache_max_entries"`
	JWKSCacheTTL                 string `json:"jwks_cache_ttl"`
	JWKSCacheMaxEntries          int    `json:"jwks_cache_max_entries"`
}

// Config contains validated runtime configuration.
type Config struct {
	PublicListenAddress          string
	InternalListenAddress        string
	CoreURL                      *url.URL
	RequestTimeout               time.Duration
	IntrospectionCacheTTL        time.Duration
	IntrospectionCacheMaxEntries int
	JWKSCacheTTL                 time.Duration
	JWKSCacheMaxEntries          int
}

// LoadConfig reads and validates a JSON configuration file.
func LoadConfig(path string) (Config, error) {
	file, err := os.Open(path)
	if err != nil {
		return Config{}, fmt.Errorf("open config: %w", err)
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	decoder.DisallowUnknownFields()

	var raw fileConfig
	if err := decoder.Decode(&raw); err != nil {
		return Config{}, fmt.Errorf("decode config: %w", err)
	}
	if err := ensureSingleJSONValue(decoder); err != nil {
		return Config{}, err
	}

	return parseConfig(raw)
}

func ensureSingleJSONValue(decoder *json.Decoder) error {
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		if err == nil {
			return errors.New("decode config: multiple JSON values")
		}
		return fmt.Errorf("decode config: %w", err)
	}
	return nil
}

func parseConfig(raw fileConfig) (Config, error) {
	if raw.PublicListenAddress == "" {
		raw.PublicListenAddress = defaultPublicListenAddress
	}
	if raw.InternalListenAddress == "" {
		raw.InternalListenAddress = defaultInternalListenAddress
	}
	if raw.PublicListenAddress == raw.InternalListenAddress {
		return Config{}, errors.New("public and internal listen addresses must differ")
	}

	coreURL, err := url.Parse(raw.CoreURL)
	if err != nil {
		return Config{}, fmt.Errorf("parse core_url: %w", err)
	}
	if coreURL.Scheme != "http" && coreURL.Scheme != "https" {
		return Config{}, errors.New("core_url must use http or https")
	}
	if coreURL.Host == "" {
		return Config{}, errors.New("core_url must include a host")
	}
	if coreURL.User != nil || coreURL.RawQuery != "" || coreURL.Fragment != "" {
		return Config{}, errors.New("core_url must not include credentials, query, or fragment")
	}

	requestTimeout, err := parseDuration(
		"request_timeout",
		raw.RequestTimeout,
		defaultRequestTimeout,
	)
	if err != nil {
		return Config{}, err
	}
	introspectionTTL, err := parseDuration(
		"introspection_cache_ttl",
		raw.IntrospectionCacheTTL,
		defaultIntrospectionCacheTTL,
	)
	if err != nil {
		return Config{}, err
	}
	jwksTTL, err := parseDuration(
		"jwks_cache_ttl",
		raw.JWKSCacheTTL,
		defaultJWKSCacheTTL,
	)
	if err != nil {
		return Config{}, err
	}

	if raw.IntrospectionCacheMaxEntries == 0 {
		raw.IntrospectionCacheMaxEntries = defaultIntrospectionCacheEntries
	}
	if raw.IntrospectionCacheMaxEntries < 0 {
		return Config{}, errors.New("introspection_cache_max_entries must be positive")
	}
	if raw.JWKSCacheMaxEntries == 0 {
		raw.JWKSCacheMaxEntries = defaultJWKSCacheEntries
	}
	if raw.JWKSCacheMaxEntries < 0 {
		return Config{}, errors.New("jwks_cache_max_entries must be positive")
	}

	return Config{
		PublicListenAddress:          raw.PublicListenAddress,
		InternalListenAddress:        raw.InternalListenAddress,
		CoreURL:                      coreURL,
		RequestTimeout:               requestTimeout,
		IntrospectionCacheTTL:        introspectionTTL,
		IntrospectionCacheMaxEntries: raw.IntrospectionCacheMaxEntries,
		JWKSCacheTTL:                 jwksTTL,
		JWKSCacheMaxEntries:          raw.JWKSCacheMaxEntries,
	}, nil
}

func parseDuration(name, value string, fallback time.Duration) (time.Duration, error) {
	if value == "" {
		return fallback, nil
	}
	duration, err := time.ParseDuration(value)
	if err != nil {
		return 0, fmt.Errorf("parse %s: %w", name, err)
	}
	if duration <= 0 {
		return 0, fmt.Errorf("%s must be positive", name)
	}
	return duration, nil
}
