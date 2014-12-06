#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re

def str_sim(a, b, do_print=False):
	a = a.lower()
	b = b.lower()

	a_parts = re.split('[\W_]+', a)
	b_parts = re.split('[\W_]+', b)

	# this is a "simple" way to declare out[a][b]
	out = list(map(list, [[0]*len(b_parts)]*len(a_parts)))

	for i in range(0, len(a_parts)-1):
		for j in range(0, len(b_parts)-1):
			if a_parts[i] == b_parts[j]:
				out[i][j] += 1

	if do_print:
		i = 0
		for j in range(0, len(b_parts)):
			print('  |'*i + ' '*2 + '.- ' + b_parts[j])
			i += 1
		print('  |'*i)

		for i in range(0, len(a_parts)):
			print(' ' + str(out[i]) + ' ' + a_parts[i])

	return out

def sum_array(array):
	_sum = 0
	for a in array:
		if list == type(a) or tuple == type(a) or hash == type(a):
			_sum += sum_array(a)
		elif int == type(a) or float == type(a):
			_sum += a
	return _sum

def wrapper_print(a, b, comment=''):
	ret = str_sim(a, b, do_print=True)

	if '' != comment:
		comment = ' ^ ' + comment

	print('[%2dx%2d::%2d]%s' %(len(ret), len(ret[0]), sum_array(ret), comment))

if '__main__' == __name__:
	pairs = (
		(
			'http://de.wikipedia.org/wiki/Monte_Kali_%28Heringen%29',
			'Monte Kali (Heringen)'
		),
		(
			'http://www.spiegel.de/politik/ausland/buddhisten-treffen-in-colombo-blitzender-moench-a-994447.html',
			'Buddhisten-Treffen in Colombo: Blitzender Mönch - SPIEGEL ONLINE'
		)
	)

	wrapper_print('foo bar baz', 'foo bar boom')

	for (url, title) in pairs:
		wrapper_print(title, url, comment='raw')
		url_no_proto = re.sub(r'https?://[^/]*/', '', url)
		wrapper_print(title, url_no_proto, comment='no proto/domain')
		url_no_proto_no_digits = re.sub(r'[0-9]*', '', url_no_proto)
		wrapper_print(title, url_no_proto_no_digits, comment='no proto/domain/[0-9]')
