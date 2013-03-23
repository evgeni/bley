test: test-setup
	trial test
	pep8 --ignore=E501,E221,E226 ./bley .
	make test-clean

test-setup: test-clean
	./bley -c ./test/bley_sqlite.conf -p ./test/bley_sqlite.pid

test-clean:
	[ ! -f ./test/bley_sqlite.pid ] || kill $$(cat ./test/bley_sqlite.pid)
	rm -f ./test/bley_sqlite.db

.PHONY: test
