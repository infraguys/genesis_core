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
	"context"
	"sync"
)

type flightCall struct {
	done     chan struct{}
	response cachedResponse
	err      error
}

type flightGroup struct {
	mu    sync.Mutex
	calls map[string]*flightCall
}

func newFlightGroup() *flightGroup {
	return &flightGroup{calls: make(map[string]*flightCall)}
}

func (group *flightGroup) do(
	ctx context.Context,
	key string,
	call func() (cachedResponse, error),
) (cachedResponse, error) {
	group.mu.Lock()
	if running, ok := group.calls[key]; ok {
		group.mu.Unlock()
		select {
		case <-running.done:
			return running.response.clone(), running.err
		case <-ctx.Done():
			return cachedResponse{}, ctx.Err()
		}
	}

	running := &flightCall{done: make(chan struct{})}
	group.calls[key] = running
	group.mu.Unlock()

	running.response, running.err = call()
	close(running.done)

	group.mu.Lock()
	delete(group.calls, key)
	group.mu.Unlock()

	return running.response.clone(), running.err
}
