jid = string
password = string
rooms = string_list(default=list('spielwiese@chat.debianforum.de',))

src-url = string

bot_nickname = string
bot_owner = string

# rate limiting
hist_max_count = integer(default=5)
hist_max_time = integer(default=10*60)

# statistics
uptime = integer(default=0)

persistent_storage = string(default='urlbot.persistent')
persistent_locked = boolean(default=false)

# the "dice" feature will use more efficient random data (0) for given users
enhanced-random-user = string_list(default=list())

# the "moin" feature will be "disabled" for given users
moin-modified-user = string_list(default=list())
moin-disabled-user = string_list(default=list())

tea_steep_time = integer(default=220)

image_preview = boolean(default=true)
dsa_watcher_interval = integer(default=900)
loglevel = option('ERROR', WARN', 'INFO', 'DEBUG', default='INFO')

debug_mode = boolean(default=false)
