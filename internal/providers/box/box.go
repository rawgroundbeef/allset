// Package box implements the native Box compute API without terminal or workspace dependencies.
package box

import (
	"bufio"
	"bytes"
	"context"
	"errors"
	"github.com/rawgroundbeef/allset/internal/config"
	"github.com/rawgroundbeef/allset/internal/execution"
	"github.com/rawgroundbeef/allset/internal/strategy"
)

type Client struct{ Executable string }

func (c Client) Info(ctx context.Context, id string) (strategy.Status, error) {
	raw, err := execution.Capture(ctx, c.Executable, "--no-update", "--json", "info", id)
	if err != nil {
		return strategy.Status{}, err
	}
	return ParseInfo(raw, id)
}

func ParseInfo(raw []byte, id string) (strategy.Status, error) {
	scanner := bufio.NewScanner(bytes.NewReader(raw))
	scanner.Buffer(make([]byte, 4096), config.MaxBytes)
	var last []byte
	for scanner.Scan() {
		if len(bytes.TrimSpace(scanner.Bytes())) > 0 {
			last = append(last[:0], scanner.Bytes()...)
		}
	}
	if err := scanner.Err(); err != nil {
		return strategy.Status{}, errors.New("invalid Box response")
	}
	var info struct {
		Success *bool `json:"success"`
		Box     *struct {
			ID           string `json:"id"`
			State        string `json:"state"`
			ArchiveAfter string `json:"archiveAfter"`
		} `json:"box"`
	}
	if err := config.Decode(last, &info, false); err != nil {
		return strategy.Status{}, errors.New("Box did not return valid JSON machine information")
	}
	if (info.Success != nil && !*info.Success) || info.Box == nil || info.Box.ID != id || info.Box.State == "" {
		return strategy.Status{}, errors.New("Box did not confirm the requested machine identity and state")
	}
	return strategy.Status{MachineID: id, State: info.Box.State, Source: "box", AutoStop: info.Box.ArchiveAfter}, nil
}
