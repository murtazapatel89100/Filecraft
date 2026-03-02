package organizer

const HistoryFilePrefix = ".organizer_history_"

var imageExtensions = []string{".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg", ".heic", ".heif", ".ico", ".raw", ".cr2", ".nef", ".orf", ".sr2", ".psd", ".ai", ".eps"}
var documentExtensions = []string{".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".pages", ".tex"}
var spreadsheetExtensions = []string{".xls", ".xlsx", ".xlsm", ".ods", ".csv", ".tsv"}
var presentationExtensions = []string{".ppt", ".pptx", ".odp", ".key"}
var videoExtensions = []string{".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".mpeg", ".mpg", ".3gp", ".m4v"}
var audioExtensions = []string{".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".aiff", ".alac"}
var archiveExtensions = []string{".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".tar.gz"}
var executableExtensions = []string{".exe", ".msi", ".apk", ".app", ".deb", ".rpm", ".dmg", ".bin", ".sh", ".bat"}
var codeExtensions = []string{".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".html", ".css", ".scss", ".json", ".xml", ".yaml", ".yml", ".sql"}
var fontExtensions = []string{".ttf", ".otf", ".woff", ".woff2", ".eot"}
var diskImageExtensions = []string{".iso", ".img", ".vhd", ".vmdk"}

var extensionTypeMap = buildExtensionTypeMap()
var knownExtensions = mapKeys(extensionTypeMap)

func buildExtensionTypeMap() map[string]string {
	extensionType := map[string]string{}

	for _, ext := range imageExtensions {
		extensionType[ext] = "IMAGES"
	}
	for _, ext := range videoExtensions {
		extensionType[ext] = "VIDEOS"
	}
	for _, ext := range audioExtensions {
		extensionType[ext] = "AUDIO"
	}
	for _, ext := range documentExtensions {
		extensionType[ext] = "DOCUMENTS"
	}
	for _, ext := range spreadsheetExtensions {
		extensionType[ext] = "SPREADSHEETS"
	}
	for _, ext := range presentationExtensions {
		extensionType[ext] = "PRESENTATIONS"
	}
	for _, ext := range archiveExtensions {
		extensionType[ext] = "ARCHIVES"
	}
	for _, ext := range executableExtensions {
		extensionType[ext] = "EXECUTABLES"
	}
	for _, ext := range codeExtensions {
		extensionType[ext] = "CODE"
	}
	for _, ext := range fontExtensions {
		extensionType[ext] = "FONTS"
	}
	for _, ext := range diskImageExtensions {
		extensionType[ext] = "DISK_IMAGES"
	}

	return extensionType
}

func mapKeys(input map[string]string) []string {
	keys := make([]string, 0, len(input))
	for k := range input {
		keys = append(keys, k)
	}
	return keys
}
