#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

from rectangle import ProbingRectangle

import random
from math import log2

dir0 = True
dir1 = False

class Hop:

	def __init__(self, capacities, e_dir0, e_dir1, balances=None, granularity=1):
		'''
			Initialize a hop.
			Parameters:
			- capacities: a list of capacities
			- e_dir0: indices of channels enabled in dir0
			- e_dir1: indices of channels enabled in dir1
			- balances: a list of balances (optional)
			By default, balances are generated randomly.
		'''
		self.N = len(capacities)
		assert(self.N > 0)
		self.can_forward_dir0 = len(e_dir0) > 0
		self.can_forward_dir1 = len(e_dir1) > 0
		# ensure validity of indices
		if self.can_forward_dir0:
			assert(max(e_dir0) <= self.N)
		if self.can_forward_dir1:
			assert(max(e_dir1) <= self.N)
		self.capacities = capacities
		self.e = {dir0: e_dir0, dir1: e_dir1}
		if balances:
			# if balances are provided, check their consistency w.r.t. capacities
			assert(all(0 <= b <= c for b,c in zip(balances, capacities)))
			self.B = balances
		else:
			# for each channel, pick a balance randomly between zero and capacity
			self.B = [random.randrange(self.capacities[i]) for i in range(self.N)]
		#print("balances", self.B)
		self.max_capacity_dir0 = max([c for i,c in enumerate(self.capacities) if i in self.e[dir0]]) if self.can_forward_dir0 else 0
		self.max_capacity_dir1 = max([c for i,c in enumerate(self.capacities) if i in self.e[dir1]]) if self.can_forward_dir1 else 0
		# h is how much a hop can _really_ forward in dir0
		self.h = max([b for i,b in enumerate(self.B) if i in self.e[dir0]]) if self.can_forward_dir0 else 0
		# g is how much a hop can _really_ forward in dir1
		self.g = max([self.capacities[i] - b for i,b in enumerate(self.B) if i in self.e[dir1]]) if self.can_forward_dir1 else 0
		self.granularity = granularity
		self.reset()


	def capacity(self):
		return sum(self.capacities)


	def __update_dependent_hop_properties(self):
		'''
			Each of the four bounds (h_l, h_u, g_l, g_u) correspond to a rectangle.
			This function updates the rectangles to reflect the current bounds.
			It must be called after every bound update (such as a probe).
		'''
		self.R_h_l = ProbingRectangle(self, is_dir0 = True,  bound = self.h_l)
		self.R_h_u = ProbingRectangle(self, is_dir0 = True,  bound = self.h_u)
		self.R_g_l = ProbingRectangle(self, is_dir0 = False, bound = self.g_l)
		self.R_g_u = ProbingRectangle(self, is_dir0 = False, bound = self.g_u)
		self.S_F = self.__S_F()
		self.uncertainty = max(0, log2(self.S_F) - log2(self.granularity))
		assert(self.h_l < self.h <= self.h_u), (self.h_l, self.h, self.h_u)
		assert(self.g_l < self.g <= self.g_u), (self.g_l, self.g, self.g_u)


	def reset(self):
		'''
			Set all variable hop parameters to their initial values.
			Must be called on initialization and before running repeated probing on the same hops.
		'''
		self.h_l = -1
		self.g_l = -1
		self.max_c_dir_0 = max([c for (i,c) in enumerate(self.capacities) if i in self.e[dir0]]) if self.can_forward_dir0 else max(self.capacities)
		self.max_c_dir_1 = max([c for (i,c) in enumerate(self.capacities) if i in self.e[dir1]]) if self.can_forward_dir1 else max(self.capacities)
		self.h_u = self.max_c_dir_0
		self.g_u = self.max_c_dir_1
		self.__update_dependent_hop_properties()


	def __str__(self):
		s = ""
		s += "Hop with properties:\n"
		s += "  channels: " + str(self.N) + "\n"
		s += "  capacities: " + str(self.capacities) + "\n"
		s += "  balances: " + str(self.B) + "\n"
		s += "  enabled in dir0: " + str(self.e[dir0]) + "\n"
		s += "  enabled in dir1: " + str(self.e[dir1]) + "\n"
		s += "  can forward in dir0: " + str(self.h) + "\n"
		s += "  can forward in dir1: " + str(self.g) + "\n"
		def effective_h(h):
			return h if self.can_forward_dir0 else 0
		def effective_g(g):
			return g if self.can_forward_dir1 else 0
		s += "Can forward in dir0 (estimate):\n"
		s += "  " + str(effective_h(self.h_l + 1)) + " -- " + str(effective_h(self.h_u)) + "\n"
		s += "Can forward in dir1 (estimate):\n"
		s += "  " + str(effective_g(self.g_l + 1)) + " -- " + str(effective_g(self.g_u)) + "\n"
		s += "Uncertainty: " + str(self.uncertainty) + "\n"
		return s


	def __assert_hop_correct(self):
		assert(-1 <= self.h_l <= self.h_u <= self.max_c_dir_0)
		assert(-1 <= self.g_l <= self.g_u <= self.max_c_dir_1)
	

	def effective_vertex(self, is_dir0, bound):
		'''
			The coordinate of the _effective vertex_ corresponding to bound in direction
			is determined by:

			* the bound itself (bound = amount - 1);
			* if the i-th channel is enabled;
			* if the bound is lower than the i-th capacity.

			If bound <= i-th capacity and the i-th channel is enabled,
			the effective vertex' i-th coordinate equals the bound,
			otherwise it equals the i-th capacity.

			The corresponding ProbingRectangle is determined by the effective vertex
			and either [0, ... 0] (for dir0) or [c_1, ... c_N] (for dir1).

			Parameters:

			- is_dir0: True if the bound corresponds to a probe in dir0, False otherwise
			- bound: equals to a - 1, where a is the probing amount
			(rationale: a probe of amount a cuts the points strictly less than a).

			Return:
			- eff_vertex: an N-element vector of coordinates of the effective vertex.
		'''
		def effective_bound(bound, ch_i):
			enabled_channels = self.e[dir0] if is_dir0 else self.e[dir1]
			# for single-channel hops, h / g bounds are not independent
			# hence, it is sufficient for channel to be enabled in one direction
			if (ch_i in enabled_channels or self.N == 1 or bound < 0) and bound <= self.capacities[ch_i]:
				eff_bound = bound
			else:
				eff_bound = self.capacities[ch_i]
			#print("effective bound:", eff_bound)
			return eff_bound
		def effective_coordinate(bound, ch_i):
			return effective_bound(bound, ch_i) if is_dir0 else self.capacities[ch_i] - effective_bound(bound, ch_i)
		eff_vertex = [effective_coordinate(bound, ch_i) for ch_i in range(self.N)]
		assert(max(eff_vertex) <= max(self.capacities) + 1), (eff_vertex, max(self.capacities))
		#print("coordinates of effective vertex for bound = ", bound, "in", ("dir0" if is_dir0 else "dir1"), ":", eff_vertex)
		return eff_vertex
	
		
	def __S_F_generic(self, R_h_l, R_h_u, R_g_l, R_g_u):
		'''
			Calculate S(F) determined by four rectangles (see paper for details).
			Note: the rectangles don't have to correspond to the current bounds.
			They just have to be "properly formed", that is:
			- R_h_l and R_h_u are "left" (lower-left vertex at [0, ... 0])
			- R_g_l and R_g_u are "right" (upper-right vertex at [c_1, ... c_N])

			We use this function to calculate both:
			- the _actual_ S(F) (using the current rectangles from self. as arguments)
			- the _potential_ S(F) if we do a probe with amount a (when doing binary search for the optimal a)

			Parameters:
			- R_h_l: a left rectangle defining the     strict lower bound on h
			- R_h_u: a left rectangle defining the non-strict upper bound on h
			- R_g_l: a left rectangle defining the     strict lower bound on g
			- R_g_u: a left rectangle defining the non-strict upper bound on g

			Return:
			- S_F: the number of points that:
			  - belong to R_h_u and R_g_u
			  - do NOT belong to R_h_l
			  - do NOT belong to R_g_l 

			The points in S_F are all possible positions of the true balances B.
		'''
		R_u_u = R_h_u.intersect_with(R_g_u)
		R_u_l = R_h_u.intersect_with(R_g_l)
		R_l_u = R_h_l.intersect_with(R_g_u)
		R_l_l = R_h_l.intersect_with(R_g_l)
		'''
		print("\nR_h_l:\n", R_h_l, R_h_l.S())
		print("\nR_h_u:\n", R_h_u, R_h_u.S())
		print("\nR_g_l:\n", R_g_l, R_g_l.S())
		print("\nR_g_u:\n", R_g_u, R_g_u.S())
		print("\nR_u_u:\n", R_u_u)
		print("\nR_u_l:\n", R_u_l)
		print("\nR_l_u:\n", R_l_u)
		print("\nR_l_l:\n", R_l_l)
		'''
		S_F = R_u_u.S() - R_u_l.S() - R_l_u.S() + R_l_l.S()
		#print(R_u_u.S(), "-", R_u_l.S(), "-", R_l_u.S(), "+", R_l_l.S(), "=", S_F)
		assert(S_F >= 0)
		return S_F


	def __S_F(self):
		'''
			Calculate the current S(F): the number of points balances may take as per current knowledge.
		'''
		return self.__S_F_generic(self.R_h_l, self.R_h_u, self.R_g_l, self.R_g_u)


	def S_F_a_expected(self, is_dir0, a):
		'''
			Calculate the _potential_ S(F) if we do a probe of amount a and it fails (aka "area under the cut").
			It doesn't matter if we assume success or failure:
			  if we find a s.t. a probe with amount a leaves S_F/2 under the cut,
			  it automatically leaves S_F/2 above the cut.
		'''
		# it we probe in dir0, only h_u and hence R_h_u changes
		new_R_h_u = ProbingRectangle(self, is_dir0 = True,  bound = a - 1) if is_dir0 else self.R_h_u
		# it we probe in dir1, only g_u and hence R_g_u changes
		new_R_g_u = ProbingRectangle(self, is_dir0 = False, bound = a - 1) if not is_dir0 else self.R_g_u
		S_F_a = self.__S_F_generic(self.R_h_l, new_R_h_u, self.R_g_l, new_R_g_u)
		#print("  expected area under the cut:", S_F_a, "(assuming failed probe)")
		return S_F_a


	def __true_balance_is_inside_F(self):
		'''
			Check that true balances are indeed inside F,
			as defined by the current bounds
		'''
		b_inside_R_h_u = self.R_h_u.contains_point(self.B)
		b_inside_R_g_u = self.R_g_u.contains_point(self.B)
		b_inside_R_h_l = self.R_h_l.contains_point(self.B)
		b_inside_R_g_l = self.R_g_l.contains_point(self.B)
		all_good = b_inside_R_h_u and b_inside_R_g_u and not b_inside_R_h_l and not b_inside_R_g_l
		# B must be within the upper bounds' rectangles
		assert(b_inside_R_h_u), 		"\nB:\n" + "\n".join([str(self.B), str(self.R_h_u)])
		assert(b_inside_R_g_u), 		"\nB:\n" + "\n".join([str(self.B), str(self.R_g_u)])
		# B must be outside the lower bounds' rectangles
		assert(not b_inside_R_h_l), 	"\nB:\n" + "\n".join([str(self.B), str(self.R_h_l)])
		assert(not b_inside_R_g_l), 	"\nB:\n" + "\n".join([str(self.B), str(self.R_g_l)])
		return all_good


	def next_a(self, is_dir0, naive):
		'''
			Calculate the optimal amount for probe in amount dir0 if is_dir0 is True, else in dir1.
			The optimal amount is the amount that decreases S(F) by half.
			(In other words, leaves S_F/2 under the cut.)
			We look for the optimal a with binary search:
			starting from the current bounds in the required direction, we choose a in the middle.
			We then check the area under the cut _if_ we probed with this amount.
			Depending on if S_F_a < S_F or S_F_a > S_F, we increase / decrease a.

			Parameters:
			- is_dir0: True to find optimal a for dir0, False for dir1

			Return:
			- a: the optimal amount, or None if the hop cannot forward in this direction
		'''
		S_F_half = max(1, self.S_F // 2)
		#print("expected area under cut = ", S_F_a, ", need", S_F_half)
		a_l, a_u = (self.h_l + 1, self.h_u) if is_dir0 else (self.g_l + 1, self.g_u)
		a = (a_l + a_u + 1) // 2
		if not naive:
			while True:
				S_F_a = self.S_F_a_expected(is_dir0, a)
				if S_F_a < S_F_half:
					a_l = a
				else:
					a_u = a
				new_a = (a_l + a_u + 1) // 2
				if new_a == a:
					break
				a = new_a
				#print("area under cut = ", S_F_a, ", need", S_F_half)
		assert(a > 0)
		return a


	def diff(self, is_dir0):
		return self.h_u - self.h_l if is_dir0 else self.g_u - self.g_l


	def fully_probed_dir(self, is_dir0):
		return self.diff(is_dir0) == 1


	def fully_probed(self):
		return self.fully_probed_dir(dir0) and self.fully_probed_dir(dir1)


	def worth_probing_dir(self, is_dir0):
		if is_dir0:
			return self.can_forward_dir0 and not self.fully_probed_dir(dir0)
		else:
			return self.can_forward_dir1 and not self.fully_probed_dir(dir1)


	def worth_probing(self):
		return self.worth_probing_dir(dir0) or self.worth_probing_dir(dir1)


	def next_dir(self, naive, prefer_small_amounts=False, threshold_area_difference=0.1):
		if not (self.worth_probing_dir(dir0) or self.worth_probing_dir(dir1)):
			print("Hop disabled in both directions:", self)
			return None
		if not self.worth_probing_dir(dir0):
			chosen_dir0 = False
		elif not self.worth_probing_dir(dir1):
			chosen_dir0 = True
		else:
			a_dir0 = self.next_a(dir0, naive)
			a_dir1 = self.next_a(dir1, naive)
			if naive or prefer_small_amounts:
				# choose smaller amount: more likely to pass
				chosen_dir0 = a_dir0 < a_dir1
			else:
				# prefer amount that splits in half better
				S_F_half = max(1, self.S_F // 2)
				S_F_a_dir0 = self.S_F_a_expected(dir0, a_dir0)
				S_F_a_dir1 = self.S_F_a_expected(dir1, a_dir1)
				if abs(S_F_a_dir0 - S_F_a_dir1) / S_F_half < threshold_area_difference:
					chosen_dir0 = a_dir0 < a_dir1
				else:
					# if the two areas
					chosen_dir0 = abs(S_F_a_dir0 - S_F_half) < abs(S_F_a_dir1 - S_F_half)
		return chosen_dir0


	def probe(self, is_dir0, amount):
		'''
			Update the bounds as a result of a probe.

			Parameters:
			- is_dir0: probe direction: dir0 if is_dir0 = True else dir1
			- amount: probe amount

			Return:
			- None (the current bounds are updated)
		'''
		#print("before probe:", self.h_l, self.h_u, self.g_l, self.g_l)
		#print("doing probe", amount, "in", "dir0" if is_dir0 else "dir1")
		should_update_dir0 = self.h_l < amount <= self.h_u and     is_dir0 and self.can_forward_dir0
		should_update_dir1 = self.g_l < amount <= self.g_u and not is_dir0 and self.can_forward_dir1
		if is_dir0:		
			probe_passed = amount <= self.h
			#print("Success?", probe_passed)
			#print("Updating estimates for this hop?", should_update_dir0)
			if should_update_dir0:
				if probe_passed:
					# sic! lower bounds are strict
					self.h_l = amount - 1
					# FIXME: in probing context, instead of self.N it should be
					# "the number of channels enabled in at least one direction (?)"
					if (self.N == 1 or should_update_dir1) and self.can_forward_dir1:
						self.g_u = self.capacities[0] - amount
				else:
					self.h_u = amount - 1
					if (self.N == 1 or should_update_dir1) and self.can_forward_dir1:
						self.g_l = self.capacities[0] - amount
		else:
			probe_passed = amount <= self.g
			#print("Success?", probe_passed)
			#print("Updating estimates for this hop?", should_update_dir1)
			if should_update_dir1:
				if probe_passed:
					self.g_l = amount - 1
					if (self.N == 1 or should_update_dir0) and self.can_forward_dir0:
						self.h_u = self.capacities[0] - amount
				else:
					self.g_u = amount - 1
					if (self.N == 1 or should_update_dir0) and self.can_forward_dir0:
						self.h_l = self.capacities[0] - amount
		#print("after probe:", self.h_l, self.h_u, self.g_l, self.g_l)
		self.__update_dependent_hop_properties()
		assert(self.__true_balance_is_inside_F()), str(self.B)
		self.__assert_hop_correct()
		return probe_passed


	def extract_channel_as_hop(self, channel_index):
		'''
		The simplest implementation of jamming
		'''
		assert(channel_index < self.N)
		return Hop(
			capacities = [self.capacities[channel_index]],
			e_dir0 = [0] if channel_index in self.e[dir0] else [],
			e_dir1 = [0] if channel_index in self.e[dir1] else [],
			balances = [self.B[channel_index]])


	def guess_true_balance(self, balance, channel_index):
		assert(channel_index < self.N)
		assert(balance <= self.capacities[channel_index])
		guessed = self.B[channel_index] == balance
		# updating the estimates : will partially speed up the jamming-enhanced probing
		# can only update lower bounds
		if channel_index in self.e[dir0]:
			self.h_l = max(balance - 1, self.h_l)
		if channel_index in self.e[dir1]:
			balance_dir1 = self.capacities[channel_index] - balance
			self.g_l = max(balance_dir1 - 1, self.g_l)
		self.__update_dependent_hop_properties()
		self.__assert_hop_correct()
		return guessed
		

	'''
	def jam(self, channel_index):
		if channel_index in self.e[dir0]:
			self.e[dir0].remove(channel_index)
		if channel_index in self.e[dir1]:
			self.e[dir1].remove(channel_index)
	
	def jam_all_except(self, channel_index):
		assert(channel_index < self.N)
		for n in range(self.N):
			if n != channel_index:
				self.jam(n)

	def unjam(self, channel_index):
		if channel_index not in self.e[dir0]:
			self.e[dir0].append(channel_index)
		if channel_index not in self.e[dir1]:
			self.e[dir1].append(channel_index)

	def unjam_all(self):
		for n in range(self.N):
			self.unjam(n)
	'''