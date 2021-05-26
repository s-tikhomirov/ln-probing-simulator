#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

import statistics
import os

from matplotlib import pyplot as plt

SAVE_RESULTS_TO = 'results'

def plot(x_data, y_data_list, x_label, y_label, title, filename, extension=".png"):
	# we assume each item in data_list is a tuple (data, label)
	# where data is a list of points corresponding to the number of channels from 1 to len(data)+1
	LABELSIZE = 20
	LEGENDSIZE = 18
	TICKSIZE = 18
	FIGSIZE = (12,7)
	#linestyles = ['-', '--', '-.', ':']
	plt.figure(figsize=FIGSIZE)
	for data in y_data_list:
		data_means = [statistics.mean(data_i) 		for data_i in data[0]]
		data_stdevs = [statistics.stdev(data_i) 	for data_i in data[0]]
		linestyle = data[2] if data[2] else "-"
		color = data[3] if data[3] else None
		if color:
			plt.errorbar(x_data, data_means,
				yerr=data_stdevs,
				fmt=linestyle,
				color=data[3],
				label=data[1])
		else:
			plt.errorbar(x_data, data_means,
				yerr=data_stdevs,
				fmt=linestyle,
				label=data[1])
	plt.xlabel(x_label, fontsize=LABELSIZE)
	plt.ylabel(y_label, fontsize=LABELSIZE)
	plt.xlim([0, max(x_data) + 1])
	plt.ylim([0, 1.1])
	#plt.tight_layout()
	plt.tick_params(axis='x', labelsize=TICKSIZE)
	plt.tick_params(axis='y', labelsize=TICKSIZE)
	plt.legend(fontsize=LEGENDSIZE)#, loc='best', bbox_to_anchor=(0.5, 0., 0.5, 0.5))
	plt.title(title, fontsize=LABELSIZE)
	plt.savefig(os.path.join(SAVE_RESULTS_TO, filename + extension))
	plt.clf()