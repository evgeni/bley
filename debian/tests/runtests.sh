cp test/whitelist_* /etc/bley
grep -v '^db' test/bley_test.conf.in > /etc/bley/bley.conf
sed -i '/log_file/ s#.*#log_file = /tmp/bley.log#' /etc/bley/bley.conf
service bley stop
service bley start
trial3 test/test_*.py
