// Package controller ships the compatibility runtime as part of the Go binary.
// Runtime source is versioned here; project profiles, credentials and VM state
// remain in the developer's existing private state directory.
package controller

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"embed"
	"encoding/base64"
	"fmt"
	"io/fs"
	"path"
	"strings"
)

// Explicit allowlist: adding private JSON or operational notes beside these
// sources must never cause them to be embedded in a distributable executable.
//
//go:embed runtime/progress.py runtime/box-herdr.py runtime/projects.py runtime/project_shell.py runtime/profiles.py
//go:embed runtime/agent_auth.py runtime/agent_credentials.py runtime/github_auth.py runtime/infisical_context.py
//go:embed runtime/onboarding.py runtime/session_context.py runtime/skills.py
//go:embed runtime/repository_access.py runtime/worker.py runtime/bootstrap.sh runtime/prepare.sh
//go:embed runtime/app-runtime.py runtime/service-exec.py runtime/preview-gateway.mjs runtime/preview-tunnel.py
var sources embed.FS

//go:embed bootstrap.py
var bootstrap string

var payload = archive()

// Revision identifies the exact embedded runtime bytes, independently of state.
var Revision = fmt.Sprintf("%x", sha256.Sum256(payload))

func archive() []byte {
	var buffer bytes.Buffer
	writer := zip.NewWriter(&buffer)
	entries, err := fs.ReadDir(sources, "runtime")
	if err != nil {
		panic(err)
	}
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() || !(strings.HasSuffix(name, ".py") || strings.HasSuffix(name, ".sh") || strings.HasSuffix(name, ".mjs")) {
			panic("unexpected controller asset: " + name)
		}
		data, err := sources.ReadFile(path.Join("runtime", name))
		if err != nil {
			panic(err)
		}
		file, err := writer.CreateHeader(&zip.FileHeader{Name: name, Method: zip.Deflate})
		if err != nil {
			panic(err)
		}
		if _, err := file.Write(data); err != nil {
			panic(err)
		}
	}
	if err := writer.Close(); err != nil {
		panic(err)
	}
	return buffer.Bytes()
}

// Arguments defers materialization until execution, keeping plans and diagnosis
// read-only. Isolated Python imports only the bundled runtime and standard library.
func Arguments(state, box, herdr string, command []string) []string {
	script := "_ARCHIVE = " + fmt.Sprintf("%q", base64.StdEncoding.EncodeToString(payload)) + "\n" + bootstrap
	return append([]string{"-I", "-S", "-c", script, state, box, herdr}, command...)
}
