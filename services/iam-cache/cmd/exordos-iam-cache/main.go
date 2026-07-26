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

package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/exordos/exordos_core/services/iam-cache/internal/app"
)

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	configPath := flag.String(
		"config",
		"/etc/exordos_core/iam_cache.json",
		"path to the JSON configuration file",
	)
	flag.Parse()

	config, err := app.LoadConfig(*configPath)
	if err != nil {
		return err
	}
	proxy := app.NewProxy(config)

	publicServer := newHTTPServer(
		config.PublicListenAddress,
		proxy.PublicHandler(),
	)
	internalServer := newHTTPServer(
		config.InternalListenAddress,
		proxy.InternalHandler(),
	)

	runContext, stop := signal.NotifyContext(
		context.Background(),
		syscall.SIGINT,
		syscall.SIGTERM,
	)
	defer stop()

	serverErrors := make(chan error, 2)
	startServer("public", publicServer, serverErrors)
	startServer("internal", internalServer, serverErrors)

	var runErr error
	select {
	case <-runContext.Done():
	case runErr = <-serverErrors:
		stop()
	}

	shutdownContext, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	publicErr := publicServer.Shutdown(shutdownContext)
	internalErr := internalServer.Shutdown(shutdownContext)
	return errors.Join(runErr, publicErr, internalErr)
}

func newHTTPServer(address string, handler http.Handler) *http.Server {
	return &http.Server{
		Addr:              address,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
}

func startServer(
	name string,
	server *http.Server,
	errorsChannel chan<- error,
) {
	go func() {
		log.Printf("%s listener started on %s", name, server.Addr)
		err := server.ListenAndServe()
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			errorsChannel <- fmt.Errorf("%s listener: %w", name, err)
		}
	}()
}

func init() {
	log.SetOutput(os.Stderr)
	log.SetFlags(log.Ldate | log.Ltime | log.LUTC)
}
