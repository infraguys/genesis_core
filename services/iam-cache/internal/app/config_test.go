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
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestLoadConfigAppliesDefaults(t *testing.T) {
	t.Parallel()

	path := writeTestConfig(t, `{"core_url":"https://core.example/api/core"}`)
	config, err := LoadConfig(path)
	if err != nil {
		t.Fatalf("LoadConfig returned an error: %v", err)
	}

	if got, want := config.PublicListenAddress, defaultPublicListenAddress; got != want {
		t.Errorf("PublicListenAddress = %q, want %q", got, want)
	}
	if got, want := config.InternalListenAddress, defaultInternalListenAddress; got != want {
		t.Errorf("InternalListenAddress = %q, want %q", got, want)
	}
	if got, want := config.RequestTimeout, defaultRequestTimeout; got != want {
		t.Errorf("RequestTimeout = %s, want %s", got, want)
	}
	if got, want := config.IntrospectionCacheTTL, defaultIntrospectionCacheTTL; got != want {
		t.Errorf("IntrospectionCacheTTL = %s, want %s", got, want)
	}
	if got, want := config.IntrospectionCacheTTL, 15*time.Second; got != want {
		t.Errorf("IntrospectionCacheTTL = %s, want deployed default %s", got, want)
	}
	if got, want := config.JWKSCacheTTL, defaultJWKSCacheTTL; got != want {
		t.Errorf("JWKSCacheTTL = %s, want %s", got, want)
	}
	if got, want := config.JWKSCacheTTL, time.Minute; got != want {
		t.Errorf("JWKSCacheTTL = %s, want deployed default %s", got, want)
	}
}

func TestLoadConfigReadsIndependentCacheTTLs(t *testing.T) {
	t.Parallel()

	path := writeTestConfig(t, `{
		"core_url":"http://core.example:8080/api/core",
		"request_timeout":"2s",
		"introspection_cache_ttl":"17s",
		"jwks_cache_ttl":"23m"
	}`)
	config, err := LoadConfig(path)
	if err != nil {
		t.Fatalf("LoadConfig returned an error: %v", err)
	}

	if got, want := config.RequestTimeout, 2*time.Second; got != want {
		t.Errorf("RequestTimeout = %s, want %s", got, want)
	}
	if got, want := config.IntrospectionCacheTTL, 17*time.Second; got != want {
		t.Errorf("IntrospectionCacheTTL = %s, want %s", got, want)
	}
	if got, want := config.JWKSCacheTTL, 23*time.Minute; got != want {
		t.Errorf("JWKSCacheTTL = %s, want %s", got, want)
	}
}

func TestLoadConfigRejectsUnknownFields(t *testing.T) {
	t.Parallel()

	path := writeTestConfig(t, `{
		"core_url":"https://core.example",
		"introspection_ttl":"15s"
	}`)
	_, err := LoadConfig(path)
	if err == nil || !strings.Contains(err.Error(), "unknown field") {
		t.Fatalf("LoadConfig error = %v, want unknown field error", err)
	}
}

func TestLoadConfigRejectsInvalidValues(t *testing.T) {
	t.Parallel()

	tests := map[string]string{
		"missing Core URL":            `{}`,
		"unsupported Core scheme":     `{"core_url":"ftp://core.example"}`,
		"non-positive cache size":     `{"core_url":"https://core.example","jwks_cache_max_entries":-1}`,
		"non-positive cache lifetime": `{"core_url":"https://core.example","jwks_cache_ttl":"0s"}`,
		"shared listener": `{
			"core_url":"https://core.example",
			"public_listen_address":":8080",
			"internal_listen_address":":8080"
		}`,
	}

	for name, contents := range tests {
		t.Run(name, func(t *testing.T) {
			t.Parallel()
			path := writeTestConfig(t, contents)
			if _, err := LoadConfig(path); err == nil {
				t.Fatal("LoadConfig returned no error")
			}
		})
	}
}

func writeTestConfig(t *testing.T, contents string) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(path, []byte(contents), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}
	return path
}
