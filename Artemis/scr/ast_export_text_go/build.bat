go mod init ast_export
go mod tidy
go get github.com/yuin/gopher-lua
go build ast_export.go