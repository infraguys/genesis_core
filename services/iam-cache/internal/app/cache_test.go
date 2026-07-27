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
	"net/http"
	"testing"
	"time"
)

func TestIntrospectionCacheUsesBothIndexes(t *testing.T) {
	t.Parallel()

	cache := newIntrospectionCache(time.Minute, 10)
	now := time.Date(2026, 7, 26, 12, 0, 0, 0, time.UTC)
	cache.now = func() time.Time { return now }
	response := testCachedResponse(`{"permissions":["read"]}`)

	epoch := cache.currentEpoch()
	for _, token := range []string{"access-one", "access-two"} {
		if !cache.put(
			token,
			"6ba7b810-9dad-11d1-80b4-00c04fd430c8",
			"client-one",
			now.Add(time.Hour),
			response,
			epoch,
		) {
			t.Fatalf("put(%q) returned false", token)
		}
	}

	if _, ok := cache.get("access-one", "client-one"); !ok {
		t.Fatal("first access token was not found")
	}
	if _, ok := cache.get("access-two", "client-one"); !ok {
		t.Fatal("second access token was not found")
	}
	if _, ok := cache.get("access-one", "client-two"); ok {
		t.Fatal("entry was returned for a different IAM client")
	}

	if got, want := cache.invalidate(
		"6ba7b810-9dad-11d1-80b4-00c04fd430c8",
	), 2; got != want {
		t.Fatalf("invalidate() = %d, want %d", got, want)
	}
	if _, ok := cache.get("access-one", "client-one"); ok {
		t.Fatal("first access token survived invalidation")
	}
	if _, ok := cache.get("access-two", "client-one"); ok {
		t.Fatal("second access token survived invalidation")
	}
}

func TestIntrospectionCacheHonorsTTLAndTokenExpiration(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, 7, 26, 12, 0, 0, 0, time.UTC)
	response := testCachedResponse(`{"permissions":[]}`)

	tests := map[string]struct {
		cacheTTL        time.Duration
		tokenExpiration time.Time
		advance         time.Duration
	}{
		"configured TTL": {
			cacheTTL:        30 * time.Second,
			tokenExpiration: now.Add(time.Hour),
			advance:         31 * time.Second,
		},
		"token expiration": {
			cacheTTL:        time.Hour,
			tokenExpiration: now.Add(10 * time.Second),
			advance:         11 * time.Second,
		},
	}

	for name, test := range tests {
		t.Run(name, func(t *testing.T) {
			cache := newIntrospectionCache(test.cacheTTL, 10)
			currentTime := now
			cache.now = func() time.Time { return currentTime }

			if !cache.put(
				"access",
				"6ba7b810-9dad-11d1-80b4-00c04fd430c8",
				"client",
				test.tokenExpiration,
				response,
				cache.currentEpoch(),
			) {
				t.Fatal("put() returned false")
			}
			currentTime = currentTime.Add(test.advance)
			if _, ok := cache.get("access", "client"); ok {
				t.Fatal("expired entry was returned")
			}
		})
	}
}

func TestIntrospectionInvalidationFencesInFlightStore(t *testing.T) {
	t.Parallel()

	cache := newIntrospectionCache(time.Minute, 10)
	now := time.Date(2026, 7, 26, 12, 0, 0, 0, time.UTC)
	cache.now = func() time.Time { return now }

	epoch := cache.currentEpoch()
	cache.invalidate("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
	if cache.put(
		"access",
		"6ba7b810-9dad-11d1-80b4-00c04fd430c8",
		"client",
		now.Add(time.Hour),
		testCachedResponse(`{"permissions":[]}`),
		epoch,
	) {
		t.Fatal("stale in-flight result was stored after invalidation")
	}
}

func TestCachesEvictLeastRecentlyUsedEntries(t *testing.T) {
	t.Parallel()

	now := time.Date(2026, 7, 26, 12, 0, 0, 0, time.UTC)
	introspection := newIntrospectionCache(time.Hour, 2)
	introspection.now = func() time.Time { return now }
	epoch := introspection.currentEpoch()
	for _, token := range []string{"one", "two"} {
		introspection.put(
			token,
			token+"-uuid",
			"client",
			now.Add(time.Hour),
			testCachedResponse(token),
			epoch,
		)
	}
	if _, ok := introspection.get("one", "client"); !ok {
		t.Fatal("recently used entry not found")
	}
	introspection.put(
		"three",
		"three-uuid",
		"client",
		now.Add(time.Hour),
		testCachedResponse("three"),
		epoch,
	)
	if _, ok := introspection.get("two", "client"); ok {
		t.Fatal("least recently used introspection entry was not evicted")
	}

	jwks := newJWKSCache(time.Hour, 1)
	jwks.now = func() time.Time { return now }
	jwks.put("client-one", testCachedResponse("one"))
	jwks.put("client-two", testCachedResponse("two"))
	if _, ok := jwks.get("client-one"); ok {
		t.Fatal("least recently used JWKS entry was not evicted")
	}
	if _, ok := jwks.get("client-two"); !ok {
		t.Fatal("newest JWKS entry not found")
	}
}

func testCachedResponse(body string) cachedResponse {
	return cachedResponse{
		statusCode: http.StatusOK,
		header:     http.Header{"Content-Type": []string{"application/json"}},
		body:       []byte(body),
	}
}
