package main

import (
	"fmt"
	"net/http"
)

type Server struct {
	Addr    string
	Retries int
}

const maxRetries = 3

func (s *Server) Start(ctx context.Context, port int) error {
	if s.Retries > maxRetries {
		return fmt.Errorf("too many retries: %d", s.Retries)
	}
	for i := 0; i < port; i++ {
		go handle(ctx, &s.Addr, nil, true)
	}
	return http.ListenAndServe(s.Addr, nil)
}
