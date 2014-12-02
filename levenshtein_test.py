#!/usr/bin/python3

from common import levenshtein

(a, b) = ('foo barbaz', 'foobar baz')
(a, b) = ('sitting', 'kitten')
(a, b) = ('Monte Kali (Heringen)', 'http://de.wikipedia.org/wiki/Monte_Kali_%28Heringen%29')

(matrix, ret) = levenshtein(a, b, return_table=True)

sep = ' '*0
out = ''
for B in b:
	out += sep + '%2s' % B
print(sep + ' '*4 + out)

for i in range(len(matrix)):
	if 0 == i:
		out = '  '
	else:
		out = '%2s' % a[i-1]

	for j in range(len(matrix[i])):
		if 0 == i or 0 == j:
			col = '30;42'
		elif i == j:
			col = '41'
		else:
			col = 0

		if 0 != col:
			out += sep + '\x1b[%sm%2d\x1b[m' %(col, matrix[i][j])
		else:
			out += sep + '%2d' % matrix[i][j]

	print(out)

print(ret)
