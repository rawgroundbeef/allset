package config

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
)

func registry() File {
	return File{Version: 3, Projects: []Project{{Name: "shop-app", Aliases: []string{"shop"}, Repository: "example/shop", Backend: "box"}}}
}

func TestEquivalentRepositoryIdentity(t *testing.T) {
	f := registry()
	for _, remote := range []string{"example/shop", "https://github.com/EXAMPLE/shop.git", "git@github.com:example/shop.git", "ssh://git@github.com/example/shop.git"} {
		p, err := f.ResolveRepository(remote)
		if err != nil || p.Name != "shop-app" {
			t.Fatalf("remote=%q project=%v err=%v", remote, p, err)
		}
	}
	if _, err := f.ResolveRepository("other/private"); err == nil {
		t.Fatal("unregistered repository inferred")
	}
}

func TestRejectAmbiguousOrUnsafeBindings(t *testing.T) {
	for _, edit := range []func(*File){
		func(f *File) { f.Projects[0].Name = "../work" },
		func(f *File) { f.Projects[0].Aliases = []string{"stop"} },
		func(f *File) { f.Projects[0].Aliases = []string{"shop-app"} },
		func(f *File) {
			f.Projects = append(f.Projects, Project{Name: "work", Aliases: []string{"shop"}, Repository: "org/work", Backend: "box"})
		},
		func(f *File) {
			f.Projects = append(f.Projects, Project{Name: "work", Repository: "git@github.com:example/shop.git", Backend: "box"})
		},
		func(f *File) { f.Projects[0].Repository = "https://SECRET@github.com/example/shop" },
		func(f *File) { f.Projects[0].Repository = "https://github.com/example/shop?token=SECRET" },
		func(f *File) { f.Projects[0].Repository = "https://github.com/org/../repo" },
		func(f *File) { f.Projects[0].Backend = "../invalid" },
	} {
		f := registry()
		edit(&f)
		if err := f.Validate(); err == nil {
			t.Fatalf("accepted %+v", f)
		} else if bytes.Contains([]byte(err.Error()), []byte("SECRET")) {
			t.Fatal("credential leaked in error")
		}
	}
}

func TestStrictJSON(t *testing.T) {
	for _, raw := range []string{
		`{"version":1,"version":2,"projects":[]}`,
		`{"version":1,"projects":[],"agents":{"token":"SECRET"}}`,
		`{"version":1,"projects":[]} {}`,
		`{"version":"SECRET","projects":[]}`,
		`{"version":1,"projects":[{"name":"hey","name":"work"}]}`,
		`{"version":1,"projects":null}`,
		`{"version":1,"projects":[],"$schema":null}`,
		`{"version":1,"projects":[{"aliases":null}]}`,
	} {
		var f File
		err := Decode([]byte(raw), &f, true)
		if err == nil {
			t.Fatalf("accepted %s", raw)
		}
		if bytes.Contains([]byte(err.Error()), []byte("SECRET")) {
			t.Fatal("echoed config values")
		}
	}
	var f File
	if Decode(bytes.Repeat([]byte(" "), MaxBytes+1), &f, true) == nil {
		t.Fatal("accepted oversized input")
	}
	var arbitrary any
	if Decode([]byte(strings.Repeat("[", 1000)+strings.Repeat("]", 1000)), &arbitrary, false) == nil {
		t.Fatal("accepted excessive nesting")
	}
}

func TestLocalSchemaReferenceRoundTripAndRequiredProjects(t *testing.T) {
	f := registry()
	f.Schema = "registry.schema.json"
	path := filepath.Join(t.TempDir(), "config.json")
	if err := WriteNew(path, f); err != nil {
		t.Fatal(err)
	}
	loaded, err := Load(path)
	if err != nil || loaded.Schema != f.Schema || loaded.Projects[0].Name != "shop-app" {
		t.Fatal(loaded, err)
	}
	for _, schema := range []string{"https://SECRET@example.com/schema.json", "invented.json"} {
		f.Schema = schema
		if err := f.Validate(); err == nil || strings.Contains(err.Error(), "SECRET") {
			t.Fatal("invalid schema reference accepted or echoed")
		}
	}
	if err := os.WriteFile(path, []byte(`{"version":1}`), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(path); err == nil {
		t.Fatal("missing projects treated as an empty registry")
	}
	var schema map[string]json.RawMessage
	if err := json.Unmarshal([]byte(RegistrySchema), &schema); err != nil {
		t.Fatal(err)
	}
	if string(schema["additionalProperties"]) != "false" {
		t.Fatal("schema does not reject unsupported fields")
	}
}

func TestConcurrentWriteNeverClobbersOrPublishesPartialConfig(t *testing.T) {
	path := filepath.Join(t.TempDir(), "registry", "config.json")
	var count atomic.Int32
	var wg sync.WaitGroup
	for i := 0; i < 12; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if WriteNew(path, registry()) == nil {
				count.Add(1)
			}
		}()
	}
	wg.Wait()
	if count.Load() != 1 {
		t.Fatalf("successful writers = %d", count.Load())
	}
	if _, err := Load(path); err != nil {
		t.Fatal(err)
	}
	info, _ := os.Stat(path)
	if info.Mode().Perm() != 0600 {
		t.Fatalf("mode %o", info.Mode().Perm())
	}
	before, _ := os.ReadFile(path)
	if WriteNew(path, File{Version: 3}) == nil {
		t.Fatal("overwrote existing registry")
	}
	after, _ := os.ReadFile(path)
	if !bytes.Equal(before, after) {
		t.Fatal("existing file changed")
	}
	link := filepath.Join(filepath.Dir(path), "link.json")
	if err := os.Symlink(path, link); err != nil {
		t.Fatal(err)
	}
	if WriteNew(link, registry()) == nil {
		t.Fatal("overwrote symlink")
	}
}
