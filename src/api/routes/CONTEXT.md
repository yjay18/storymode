# API Routes Context

This folder contains `/api/v1` and health route adapters. A handler parses a transport
DTO, calls one injected use case, and maps its typed result/error. It contains no
mechanics, repository path access, prompt construction, or direct model calls.
