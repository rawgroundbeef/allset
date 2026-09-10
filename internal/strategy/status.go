package strategy

type Status struct {
	Project   string `json:"project"`
	MachineID string `json:"machine_id,omitempty"`
	State     string `json:"state"`
	Source    string `json:"source"`
	CheckedAt string `json:"checked_at"`
	AutoStop  string `json:"auto_stop,omitempty"`
}
