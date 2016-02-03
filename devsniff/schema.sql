DROP TABLE IF EXISTS proxy_requests;
CREATE TABLE proxy_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, method VARCHAR(12), uri VARCHAR(4092), headers TEXT, body BLOB, host VARCHAR(1020), path VARCHAR(4092), content_encoding VARCHAR(60), content_length INTEGER, mimetype VARCHAR(60));
DROP TABLE IF EXISTS  proxy_responses;
CREATE TABLE proxy_responses(id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER, status_code INTEGER, headers TEXT, body BLOB, content_encoding VARCHAR(60), content_length INTEGER, mimetype VARCHAR(60));
