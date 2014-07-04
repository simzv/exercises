# -*- encoding: utf-8 -*-

import unittest
from fmt import Formatter


class BasicTests(unittest.TestCase):
    
    def setUp(self):
        self.linesize = 80
        self.tabsize = 4
        
        self.formatter = Formatter(linesize=self.linesize,
                                   tabsize=self.tabsize)
    
    def test_empty_formatter(self):
        out = self.formatter.get_lines()
        self.assertIsNone(out)

    def test_header_with_ending_sign(self):
        header = "Header!\n"
        self.formatter.parse_line(header)
        out = self.formatter.get_lines()
        self.assertEqual([" "*self.tabsize + header], out)

    def test_header_no_ending_sign(self):
        header = "Header\n"
        self.formatter.parse_line(header)
        out = self.formatter.get_lines()
        self.assertIsNone(out)
        self.formatter.parse_line('\n')
        out = self.formatter.get_lines()
        self.assertEqual([" "*self.tabsize + header], out)

    def test_one_line_paragraph_with_ending_sign(self):
        line = "Lorem ipsum dolor sit amet, consectetur adipisicing elit.\n"
        expected_line = ("    Lorem   ipsum   dolor    sit    amet,"
                         "    consectetur    adipisicing    elit.\n")
        self.formatter.parse_line(line)
        out = self.formatter.get_lines()
        self.assertEqual([expected_line], out)

    def test_one_line_paragraph_no_ending_sign(self):
        line = "Lorem ipsum dolor sit amet, consectetur adipisicing elit\n"
        expected_line = ("    Lorem   ipsum    dolor    sit    amet,"
                         "    consectetur    adipisicing    elit\n")
        self.formatter.parse_line(line)
        out = self.formatter.get_lines()
        self.assertIsNone(out)
        self.formatter.parse_line('\n')
        out = self.formatter.get_lines()
        self.assertEqual([expected_line], out)

    def test_last_line_of_multiline_paragraph_with_ending_sign(self):
        self.formatter._is_new_paragraph = False
        line = "lorem ipsum dolor sit amet, consectetur adipisicing elit.\n"
        self.formatter.parse_line(line)
        out = self.formatter.get_lines()
        self.assertEqual([line], out)

    def test_last_line_of_multiline_paragraph_no_ending_sign(self):
        self.formatter._is_new_paragraph = False
        line = "lorem ipsum dolor sit amet, consectetur adipisicing elit\n"
        self.formatter.parse_line(line)
        out = self.formatter.get_lines()
        self.assertIsNone(out)
        self.formatter.parse_line('\n')
        out = self.formatter.get_lines()
        self.assertEqual([line], out)

    def test_line_appending(self):
        first_line = "Lorem ipsum dolor sit amet, consectetur adipisicing\n"
        second_line = (" elit seddoeius modtem porafasdf incididunt ut labore"
                       " et dolore magna aliqua.\n")
        expected_first_line = ("    Lorem ipsum dolor sit amet, consectetur"
                               " adipisicing  elit  seddoeius  modtem\n")
        expected_second_line = ("porafasdf incididunt ut labore et dolore"
                                " magna aliqua.\n")
        self.formatter.parse_line(first_line)
        out = self.formatter.get_lines()
        self.assertIsNone(out)
        self.formatter.parse_line(second_line)
        out = self.formatter.get_lines()
        self.assertEqual([expected_first_line, expected_second_line], out)

    def test_long_line_splitting(self):
        line = ("Excepteur sint occaecat cupidatat non proident, sunt in culpa"
                " qui officia deserunt mollit anim id est laborum.\n")
        expected_first_line = ("    Excepteur sint occaecat cupidatat non"
                               " proident, sunt in  culpa  qui  officia\n")
        expected_second_line = "deserunt mollit anim id est laborum.\n"
        self.formatter.parse_line(line)
        out = self.formatter.get_lines()
        self.assertEqual([expected_first_line, expected_second_line], out)

    def test_utf8_line(self):
        line = u"Селдон больше не пытался задерживать сопровождающих.\n"
        line = line.encode('utf8')
        expected_line = (u"    Селдон     больше      не      пытался"
                         u"      задерживать      сопровождающих.\n")
        expected_line = expected_line.encode('utf8')
        self.formatter.parse_line(line)
        out = self.formatter.get_lines()
        self.assertEqual([expected_line], out)

    def test_non_utf8_line(self):
        line = u"Селдон больше не пытался задерживать сопровождающих.\n"
        line = line.encode('cp1251')
        expected_line = (u"    Селдон     больше      не      пытался"
                         u"      задерживать      сопровождающих.\n")
        expected_line = expected_line.encode('cp1251')
        self.formatter.parse_line(line)
        out = self.formatter.get_lines(flush=True)
        self.assertEqual([expected_line], out)
