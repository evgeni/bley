test: test-psql test-sqlite
	pep8 --ignore=E501,E221,E226 ./bley .
	make test-clean

test-sqlite: test-setup-sqlite
	trial test

test-setup-sqlite: test-clean
	./bley -c ./test/bley_sqlite.conf -p ./test/bley_test.pid

test-psql:
	pg_virtualenv make test-psql-real

test-psql-real: test-setup-psql
	trial test

test-setup-psql: test-clean
	sed "s#DBHOST#$$PGHOST#;s#DBPORT#$$PGPORT#;s#DBUSER#$$PGUSER#;s#DBPASS#$$PGPASSWORD#" ./test/bley_psql.conf.in > ./test/bley_psql.conf
	createdb bley_test
	./bley -c ./test/bley_psql.conf -p ./test/bley_test.pid

test-clean:
	[ ! -f ./test/bley_test.pid ] || kill $$(cat ./test/bley_test.pid)
	rm -f ./test/bley_sqlite.db ./test/bley_psql.conf

.PHONY: test
