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
			An intersection of two rectangles is a rectangles.
			We assume that one of the rectangles is "lower-left" and the other is "upper-right".

			Parameters:
			- other_rectangle: the other rectangle

			Return:
			- the intersection Rectangle or EmptyRectangle if the intersection is empty
		'''
		our_l_inside_them = other_rectangle.contains_point(self.l_vertex)
		our_u_inside_them = other_rectangle.contains_point(self.u_vertex)
		their_l_inside_us = self.contains_point(other_rectangle.l_vertex)
		their_u_inside_us = self.contains_point(other_rectangle.u_vertex)
		if our_l_inside_them and our_u_inside_them:
			result = self
		elif their_l_inside_us and their_u_inside_us:
			result = other_rectangle
		elif our_u_inside_them:
			# we are "lower", they are "upper"
			result = Rectangle(other_rectangle.l_vertex, self.u_vertex)
		elif our_l_inside_them:
			# they are "lower", we are "upper"
			result = Rectangle(self.l_vertex, other_rectangle.u_vertex)
		else:
			result = EmptyRectangle()
		return result


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

