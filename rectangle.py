#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

import operator
from functools import reduce


class Rectangle():
	'''
		A class for a generic N-dimensional rectangle defined by two opposing vertices.
		(This does not immediately relate to probing.)
	'''

	def __init__(self, l_vertex, u_vertex):
		if l_vertex and u_vertex:
			assert(len(l_vertex) == len(u_vertex))
			self.non_empty = all(coord_l <= coord_u for coord_l, coord_u in zip(l_vertex, u_vertex))
			self.l_vertex = l_vertex if self.non_empty else None
			self.u_vertex = u_vertex if self.non_empty else None
		else:
			self.non_empty = False
			self.l_vertex = None
			self.u_vertex = None


	def S(self):
		'''
			Calculate the are of the rectangle.
			The area is the product of the widths of its sides.
			(All boundaries are inclusive.)
		'''
		if self.non_empty:
			widths = [max(0, coord_u - coord_l + 1) for coord_l, coord_u in zip(self.l_vertex, self.u_vertex)]
			return reduce(operator.mul, widths, 1)
		return 0


	def __str__(self):
		s = "\n"
		if self.non_empty:
			s += "Rectangle with vertices:\n"
			s += str(self.l_vertex) + "\n"
			s += str(self.u_vertex)
		else:
			s = "\nEmpty figure"
		return s


	def contains_point(self, point):
		'''
			Return True if a given point is inside the rectangle, False otherwise.
		'''
		if self.non_empty and point is not None:
			assert(len(point) == len(self.l_vertex))
			lcond = all(l <= p for l,p in zip(self.l_vertex, point))
			ucond = all(p <= u for p,u in zip(point, self.u_vertex))
			return lcond and ucond
		return False


	def intersect_with(self, other_rectangle):
		'''
			Intersect self with another rectangle.
			An intersection of two rectangles is a rectangle.

			Parameters:
			- other_rectangle: the other rectangle

			Return:
			- the intersection Rectangle or EmptyRectangle if the intersection is empty

		'''
		if not (self.non_empty and other_rectangle.non_empty):
			# anything intersected with empty figure is empty
			return EmptyRectangle()
		assert(len(self.l_vertex) == len(other_rectangle.l_vertex))
		N = len(self.l_vertex)
		intersection_l_vertex = [None] * N
		intersection_u_vertex = [None] * N
		# iterate through all dimensions
		for i in range(N):
			if (self.l_vertex[i] > other_rectangle.u_vertex[i] or 
				self.u_vertex[i] < other_rectangle.l_vertex[i]):
				# no intersection along one dimension => intersection is empty
				return EmptyRectangle()
			else:
				# otherwise, l is max of l's, u is min of u's
				intersection_l_vertex[i] = max(self.l_vertex[i], other_rectangle.l_vertex[i])
				intersection_u_vertex[i] = min(self.u_vertex[i], other_rectangle.u_vertex[i])
		return Rectangle(intersection_l_vertex, intersection_u_vertex)



class ProbingRectangle(Rectangle):
	'''
		A rectangle corresponding to a probe.
		If dir0, the left vertex is [0, ... 0].
		If dir1, the right vertex is [c1, ..., cN].
		The other vertex is determined by the effective probe amount along the respective dimension.
	'''
	def __init__(self, hop, is_dir0, bound):
		# bound = amount - 1
		# this makes probing rectangles inclusive - easier to intersect and calculate areas
		# bound is one of: h_l, h_u, g_l, g_u
		vertex = hop.effective_vertex(is_dir0, bound)
		l_vertex, u_vertex = ([0] * hop.N, vertex) if is_dir0 else (vertex, hop.capacities)
		Rectangle.__init__(self, l_vertex, u_vertex)


class EmptyRectangle(Rectangle):
	'''
		An empty figure (with area 0).
	'''
	def __init__(self):
		Rectangle.__init__(self, None, None)

