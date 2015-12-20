other_bots = string_list(default=list())
request_counter = integer(default=0)
start_time = integer(default=0)

[plugins]
  [[info]]
    enabled = boolean(default=true)
  last_dsa = integer(default=0)  # TODO broken

[user_pref]

[user_records]

[url_blacklist]
heise = string(default='^.*heise\.de/.*-[0-9]+\.html$')
wikipedia = string(default='^.*wikipedia\.org/wiki/.*$')
blog = string(default=string(default='^.*blog\.fefe\.de/\?ts=[0-9a-f]+$'))
ibash = string(default='^.*ibash\.de/zitat.*$')
golem = string(default='^.*golem\.de/news/.*$')
paste_debian = string(default='^.*paste\.debian\.net/((hidden|plainh?)/)?[0-9a-f]+/?$')
example = string(default='^.*example\.(org|net|com).*$')
sprunge = string(default='^.*sprunge\.us/.*$')
ftp_debian = string(default='^.*ftp\...\.debian\.org.*$')
