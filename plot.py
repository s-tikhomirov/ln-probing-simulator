#! /usr/bin/python3

'''
This file is part of Lightning Network Probing Simulator.

Copyright © 2020-2021 University of Luxembourg

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
	SOFTWARE.

SPDX-FileType: SOURCE
SPDX-FileCopyrightText: 2020-2021 University of Luxembourg
SPDX-License-Identifier: MIT
'''


import statistics
import os

from matplotlib import pyplot as plt


SAVE_RESULTS_TO = 'results'


def plot(x_data, y_data_lists, x_label, y_label, title, filename, extension=None):
	'''
		Plot data and save a plot.

		Parameters:
		- x_data: a list of data points defining the X axis
		- y_data_list: a list of list of points defining (potentially multiple) lines (their Y coordinates)
		- x_label: a label for the X axis
		- y_label: a label for the Y axis
		- title: a plot title
		- filename: filename to save to (with path)
		- extension: file extension (png, pdf)
	'''
	# we assume each item in data_list is a tuple (data, label)
	# where data is a list of points corresponding to the number of channels from 1 to len(data)+1
	LABELSIZE = 20
	LEGENDSIZE = 18
	TICKSIZE = 18
	FIGSIZE = (14,8)
	#assert(len(y_data_lists) == 2)
	fig, (ax0, ax1) = plt.subplots(1, 2, figsize=FIGSIZE, sharex=True, sharey=True)
	#fig.suptitle(title, fontsize=LABELSIZE)
	fig.add_subplot(111, frameon=False)
	# hide tick and tick label of the big axis
	plt.tick_params(labelcolor='none', which='both', top=False, bottom=False, left=False, right=False)
	plt.xlabel(x_label, fontsize=LABELSIZE)
	plt.ylabel(y_label, fontsize=LABELSIZE)
	for i, ax in enumerate((ax0, ax1)):
		for data in y_data_lists[i]:
			data_means = [statistics.mean(data_i) for data_i in data[0]]
			data_stdevs = [statistics.stdev(data_i) if len(data_i) > 1 else 0 for data_i in data[0]]
			linestyle = data[2] if data[2] else "-"
			color = data[3] if data[3] else None
			if color:
				ax.errorbar(x_data, data_means,
					yerr=data_stdevs,
					fmt=linestyle,
					color=data[3],
					label=data[1])
			else:
				ax.errorbar(x_data, data_means,
					yerr=data_stdevs,
					fmt=linestyle,
					label=data[1])
		ax.set_xlim([0, max(x_data) + 1])
		ax.set_ylim([0, 1.1])
		plt.tight_layout()
		ax.set_xticks(x_data)
		ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
		ax.tick_params(axis='x', labelsize=TICKSIZE)
		ax.tick_params(axis='y', labelsize=TICKSIZE)
		ax.legend(fontsize=LEGENDSIZE, loc='lower left')
		ax.set_title(["Non-enhanced\n", "Jamming-enhanced\n"][i], fontsize=LABELSIZE)
	path = os.path.join(SAVE_RESULTS_TO, filename)
	if extension is not None:
		plt.savefig(path + extension)
	else:
		plt.savefig(path + ".pdf")
		plt.savefig(path + ".png")
	print("Results saved to", path)
	plt.clf()

