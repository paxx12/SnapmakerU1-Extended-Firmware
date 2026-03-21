upfile: upfile.c helpers.h
	$(CC) -o upfile upfile.c -lcrypto

test: upfile
	rm -rf tmp
	mkdir -p tmp
	./upfile unpack $(FIRMWARE_FILE) tmp
	./upfile pack tmp/update.bin tmp
	md5sum $(FIRMWARE_FILE) tmp/update.bin
	cmp $(FIRMWARE_FILE) tmp/update.bin

clean:
	rm -f upfile
