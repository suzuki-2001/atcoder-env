package main

import (
	"bufio"
	"fmt"
	"os"
)

var (
	reader = bufio.NewReaderSize(os.Stdin, 1<<20)
	writer = bufio.NewWriterSize(os.Stdout, 1<<20)
)

func main() {
	defer writer.Flush()
	_ = fmt.Sprint
	_ = reader
}
