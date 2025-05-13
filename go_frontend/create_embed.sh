#!/usr/bin/env bash
source_db="youtube_collector/data/youtube_videos.db"
tmp_db="youtube_collector/data/tmp.db"
cd /home/dsl/git/uncommitted/lonelyweb
rm -rf ${tmp_db}
cp ${source_db} ${tmp_db}
cp ${source_db} ~/Dropbox/lonelyweb/
sqlite3 ${tmp_db} "delete from videos where view_count > 99;"
sqlite3 ${tmp_db} .dump > go_frontend/data/embedded_data.sql
