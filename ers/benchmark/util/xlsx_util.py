"""
Small helper for writing benchmark results to an .xlsx workbook.

Each benchmarked metric is written to its own sheet ("page"), one row at a time,
and the workbook is flushed to disk after every append so partial results survive
an interrupted run.
"""

import os

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException


class XLSXUtil:
    """
    A thin wrapper around an openpyxl Workbook that appends rows to named sheets.
    """

    def __init__(self, filename):
        """
        Opens the workbook at ``filename``, creating a fresh one if it is absent or invalid.

        :param filename: Path to the .xlsx file backing this workbook.
        """
        self.filename = filename
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.workbook = load_workbook(self.filename)
        except (FileNotFoundError, InvalidFileException):
            # No usable file yet: start a blank workbook without the default sheet.
            self.workbook = Workbook()
            default_sheet = self.workbook.active
            assert default_sheet is not None  # a fresh Workbook always has one
            self.workbook.remove(default_sheet)

    def write_to_page(self, page_name, row):
        """
        Appends a row to the given sheet, creating the sheet if needed, then saves.

        :param page_name: The name of the sheet ("page") to append to.
        :param row: An iterable of cell values forming the new row.
        """
        if page_name in self.workbook.sheetnames:
            sheet = self.workbook[page_name]
        else:
            sheet = self.workbook.create_sheet(title=page_name)

        sheet.append(row)

        self.workbook.save(self.filename)

    def close(self):
        """
        Saves and closes the underlying workbook.
        """
        self.workbook.save(self.filename)
        self.workbook.close()
