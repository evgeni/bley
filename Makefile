BLEY_VERSION := $(shell python setup.py -V)
TRIAL_VERSION := $(shell trial --version |sed "s/[^0-9]//g")
#TRIAL_FLAGS ?= $(shell test $(TRIAL_VERSION) -ge 1230 && echo "-j2")
TRIAL ?= trial

sdist:
	python setup.py sdist

test: test-psql test-sqlite
	pep8 --ignore=E501 ./bley .
	make test-clean

test-sqlite: test-setup-sqlite
	$(TRIAL) $(TRIAL_FLAGS) test/test_*.py
	-[ ! -f ./test/bley_test.pid ] || kill $$(cat ./test/bley_test.pid)
	bleygraph -c ./test/bley_sqlite.conf -d ./test/bleygraphout
	make test-clean

test-setup-sqlite: test-clean
	sed "s#.*DBPORT##;s#DBTYPE#sqlite3#;s#DBNAME#./test/bley_sqlite.db#" ./test/bley_test.conf.in > ./test/bley_sqlite.conf
	bley -c ./test/bley_sqlite.conf -p ./test/bley_test.pid

test-psql:
	pg_virtualenv make test-psql-real

test-psql-real: test-setup-psql
	$(TRIAL) $(TRIAL_FLAGS) test/test_*.py
	-[ ! -f ./test/bley_test.pid ] || kill $$(cat ./test/bley_test.pid)
	bleygraph -c ./test/bley_psql.conf -d ./test/bleygraphout
	make test-clean

test-setup-psql: test-clean
	sed "s#DBHOST#$$PGHOST#;s#DBPORT#$$PGPORT#;s#DBUSER#$$PGUSER#;s#DBPASS#$$PGPASSWORD#;s#DBTYPE#pgsql#;s#DBNAME#bley_test#" ./test/bley_test.conf.in > ./test/bley_psql.conf
	createdb bley_test
	bley -c ./test/bley_psql.conf -p ./test/bley_test.pid

test-mysql:
	my_virtualenv make test-mysql-real

test-mysql-real: test-setup-mysql
	$(TRIAL) $(TRIAL_FLAGS) test/test_*.py
	-[ ! -f ./test/bley_test.pid ] || kill $$(cat ./test/bley_test.pid)
	bleygraph -c ./test/bley_mysql.conf -d ./test/bleygraphout
	make test-clean

test-setup-mysql: test-clean
	sed "s#DBHOST#$$MYSQL_HOST#;s#DBPORT#$$MYSQL_TCP_PORT#;s#DBUSER#$$MYSQL_USER#;s#DBPASS#$$MYSQL_PWD#;s#DBTYPE#mysql#;s#DBNAME#bley_test#" ./test/bley_test.conf.in > ./test/bley_mysql.conf
	echo "CREATE DATABASE bley_test;" | mysql
	bley -c ./test/bley_mysql.conf -p ./test/bley_test.pid

test-clean:
	-[ ! -f ./test/bley_test.pid ] || kill $$(cat ./test/bley_test.pid)
	rm -f ./test/bley_sqlite.db ./test/bley_sqlite.conf ./test/bley_psql.conf ./test/bley_mysql.conf
	rm -rf ./test/bleygraphout/

.PHONY: sdist test
