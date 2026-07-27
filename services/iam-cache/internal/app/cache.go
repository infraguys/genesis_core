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
	"container/list"
	"crypto/sha256"
	"net/http"
	"sync"
	"time"
)

type cachedResponse struct {
	statusCode int
	header     http.Header
	body       []byte
}

func (response cachedResponse) clone() cachedResponse {
	return cachedResponse{
		statusCode: response.statusCode,
		header:     response.header.Clone(),
		body:       append([]byte(nil), response.body...),
	}
}

type accessTokenKey [sha256.Size]byte

func makeAccessTokenKey(accessToken string) accessTokenKey {
	return sha256.Sum256([]byte(accessToken))
}

type introspectionEntry struct {
	key        accessTokenKey
	tokenUUID  string
	clientUUID string
	response   cachedResponse
	expiresAt  time.Time
	element    *list.Element
}

type introspectionCache struct {
	mu          sync.Mutex
	ttl         time.Duration
	maxEntries  int
	now         func() time.Time
	epoch       uint64
	items       map[accessTokenKey]*introspectionEntry
	byTokenUUID map[string]map[accessTokenKey]struct{}
	lru         list.List
}

func newIntrospectionCache(ttl time.Duration, maxEntries int) *introspectionCache {
	return &introspectionCache{
		ttl:         ttl,
		maxEntries:  maxEntries,
		now:         time.Now,
		items:       make(map[accessTokenKey]*introspectionEntry),
		byTokenUUID: make(map[string]map[accessTokenKey]struct{}),
	}
}

func (cache *introspectionCache) get(
	accessToken string,
	clientUUID string,
) (cachedResponse, bool) {
	key := makeAccessTokenKey(accessToken)

	cache.mu.Lock()
	defer cache.mu.Unlock()

	entry, ok := cache.items[key]
	if !ok {
		return cachedResponse{}, false
	}
	if !cache.now().Before(entry.expiresAt) {
		cache.removeLocked(entry)
		return cachedResponse{}, false
	}
	if entry.clientUUID != clientUUID {
		return cachedResponse{}, false
	}

	cache.lru.MoveToFront(entry.element)
	return entry.response.clone(), true
}

func (cache *introspectionCache) currentEpoch() uint64 {
	cache.mu.Lock()
	defer cache.mu.Unlock()
	return cache.epoch
}

func (cache *introspectionCache) put(
	accessToken string,
	tokenUUID string,
	clientUUID string,
	tokenExpiresAt time.Time,
	response cachedResponse,
	expectedEpoch uint64,
) bool {
	key := makeAccessTokenKey(accessToken)

	cache.mu.Lock()
	defer cache.mu.Unlock()

	if cache.epoch != expectedEpoch {
		return false
	}

	expiresAt := cache.now().Add(cache.ttl)
	if tokenExpiresAt.Before(expiresAt) {
		expiresAt = tokenExpiresAt
	}
	if !cache.now().Before(expiresAt) {
		return false
	}

	if existing, ok := cache.items[key]; ok {
		cache.removeLocked(existing)
	}

	entry := &introspectionEntry{
		key:        key,
		tokenUUID:  tokenUUID,
		clientUUID: clientUUID,
		response:   response.clone(),
		expiresAt:  expiresAt,
	}
	entry.element = cache.lru.PushFront(entry)
	cache.items[key] = entry

	tokenEntries := cache.byTokenUUID[tokenUUID]
	if tokenEntries == nil {
		tokenEntries = make(map[accessTokenKey]struct{})
		cache.byTokenUUID[tokenUUID] = tokenEntries
	}
	tokenEntries[key] = struct{}{}

	for len(cache.items) > cache.maxEntries {
		oldest := cache.lru.Back()
		if oldest == nil {
			break
		}
		cache.removeLocked(oldest.Value.(*introspectionEntry))
	}
	return true
}

func (cache *introspectionCache) invalidate(tokenUUID string) int {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	cache.epoch++
	keys := cache.byTokenUUID[tokenUUID]
	evicted := len(keys)
	for key := range keys {
		if entry, ok := cache.items[key]; ok {
			cache.removeLocked(entry)
		}
	}
	return evicted
}

func (cache *introspectionCache) removeLocked(entry *introspectionEntry) {
	delete(cache.items, entry.key)
	cache.lru.Remove(entry.element)

	tokenEntries := cache.byTokenUUID[entry.tokenUUID]
	delete(tokenEntries, entry.key)
	if len(tokenEntries) == 0 {
		delete(cache.byTokenUUID, entry.tokenUUID)
	}
}

type jwksEntry struct {
	clientUUID string
	response   cachedResponse
	expiresAt  time.Time
	element    *list.Element
}

type jwksCache struct {
	mu         sync.Mutex
	ttl        time.Duration
	maxEntries int
	now        func() time.Time
	items      map[string]*jwksEntry
	lru        list.List
}

func newJWKSCache(ttl time.Duration, maxEntries int) *jwksCache {
	return &jwksCache{
		ttl:        ttl,
		maxEntries: maxEntries,
		now:        time.Now,
		items:      make(map[string]*jwksEntry),
	}
}

func (cache *jwksCache) get(clientUUID string) (cachedResponse, bool) {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	entry, ok := cache.items[clientUUID]
	if !ok {
		return cachedResponse{}, false
	}
	if !cache.now().Before(entry.expiresAt) {
		cache.removeLocked(entry)
		return cachedResponse{}, false
	}

	cache.lru.MoveToFront(entry.element)
	return entry.response.clone(), true
}

func (cache *jwksCache) put(clientUUID string, response cachedResponse) {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	if existing, ok := cache.items[clientUUID]; ok {
		cache.removeLocked(existing)
	}

	entry := &jwksEntry{
		clientUUID: clientUUID,
		response:   response.clone(),
		expiresAt:  cache.now().Add(cache.ttl),
	}
	entry.element = cache.lru.PushFront(entry)
	cache.items[clientUUID] = entry

	for len(cache.items) > cache.maxEntries {
		oldest := cache.lru.Back()
		if oldest == nil {
			break
		}
		cache.removeLocked(oldest.Value.(*jwksEntry))
	}
}

func (cache *jwksCache) removeLocked(entry *jwksEntry) {
	delete(cache.items, entry.clientUUID)
	cache.lru.Remove(entry.element)
}
