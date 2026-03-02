package organizer

type Mode string

const (
	ModeExtension        Mode = "extension"
	ModeDate             Mode = "date"
	ModeExtensionAndDate Mode = "extension_and_date"
	ModeFile             Mode = "file"
)
