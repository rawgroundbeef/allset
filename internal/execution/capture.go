// Package execution owns bounded diagnostics and terminal-preserving process plans.
package execution

import (
	"bytes"
	"context"
	"errors"
	"github.com/rawgroundbeef/allset/internal/config"
	"os/exec"
	"time"
)

// limitedBuffer prevents unbounded diagnostic output without exposing it to the user.
type limitedBuffer struct {
	buffer   bytes.Buffer
	overflow bool
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	n := len(p)
	remaining := config.MaxBytes - b.buffer.Len()
	if len(p) > remaining {
		b.overflow = true
		p = p[:remaining]
	}
	b.buffer.Write(p)
	return n, nil
}

// Capture bounds read-only child processes. Errors never include raw provider output or arguments.
func Capture(ctx context.Context, executable string, args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, executable, args...)
	var out, stderr limitedBuffer
	cmd.Stdout, cmd.Stderr = &out, &stderr
	cmd.WaitDelay = time.Second
	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			return nil, errors.New("read-only check timed out; no lifecycle operation was requested")
		}
		return nil, errors.New("read-only command failed; check that the required CLI is installed and signed in")
	}
	if out.overflow || stderr.overflow {
		return nil, errors.New("read-only command output exceeded the diagnostic limit")
	}
	return out.buffer.Bytes(), nil
}
