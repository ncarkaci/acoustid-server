CREATE DATABASE "acoustid";
CREATE DATABASE "acoustid_test";

CREATE DATABASE "acoustid_slow";
CREATE DATABASE "acoustid_slow_test";

\c acoustid
create extension intarray;
create extension pgcrypto;
create extension acoustid;
create extension cube;

\c acoustid_test
create extension intarray;
create extension pgcrypto;
create extension acoustid;
create extension cube;

\c acoustid_slow
create extension intarray;
create extension pgcrypto;
create extension acoustid;
create extension cube;

\c acoustid_slow_test
create extension intarray;
create extension pgcrypto;
create extension acoustid;
create extension cube;
