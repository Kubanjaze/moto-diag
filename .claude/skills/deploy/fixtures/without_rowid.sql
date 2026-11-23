-- Phase 293, K131: the known-bad fixture for deploy.py's dump().
-- Two tables without a rowid, shaped as FTS5's own shadow tables are:
-- `_config` keyed on one column, `_idx` keyed on two. The old dump read
-- every table through `select rowid, *`, which fails on both with
-- "no such column: rowid". A rowid table beside them is the control.
create table one_key (k text primary key, v) without rowid;
create table two_key (segid integer, term blob, pgno integer,
                      primary key (segid, term)) without rowid;
create table items (id integer primary key, title text);
create table schema_version (version integer);
insert into one_key values ('version', 4), ('pgsz', 4050);
insert into two_key values (1, x'00', 1), (1, x'3061', 2), (2, x'00', 1);
insert into items values (1, 'first');
insert into schema_version values (91);
