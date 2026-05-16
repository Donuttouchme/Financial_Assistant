from datetime import date as date_type
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AmountFormat = Literal["signed", "debit_credit"]
SignConvention = Literal["negative_is_expense", "negative_is_income"]


class CsvColumnMapping(BaseModel):
    date: int                       # 0-based column index
    description: int
    amount: Optional[int] = None    # used in 'signed' mode
    debit: Optional[int] = None     # used in 'debit_credit' mode
    credit: Optional[int] = None    # used in 'debit_credit' mode
    currency: Optional[int] = None  # per-row currency column (NEW)


class CsvImportConfig(BaseModel):
    delimiter: str = ";"
    decimal_sep: str = "."
    thousands_sep: str = ""
    date_format: str = "%Y-%m-%d"   # Python strftime format
    skip_header_rows: int = 0
    has_header: bool = False
    amount_format: AmountFormat = "signed"
    sign_convention: SignConvention = "negative_is_expense"
    cols: CsvColumnMapping
    default_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)


class ParsedRow(BaseModel):
    row_index: int                  # 0-based AFTER skip_header_rows + has_header
    date: Optional[date_type] = None
    description: str = ""
    amount: Optional[Decimal] = None
    kind_hint: Optional[Literal["income", "expense"]] = None
    is_duplicate: bool = False
    errors: list[str] = Field(default_factory=list)
    currency: Optional[str] = None  # per-row currency read from CSV (NEW)


class CsvPreviewRequest(BaseModel):
    file_content: str
    config: CsvImportConfig


class CsvPreviewResponse(BaseModel):
    rows: list[ParsedRow]


class ImportCommitRowSelection(BaseModel):
    row_index: int
    category_id: int
    is_recurring: bool = False


class ImportCommitRequest(BaseModel):
    file_content: str
    config: CsvImportConfig
    selections: list[ImportCommitRowSelection]
    default_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)


class ImportCommitResponse(BaseModel):
    imported: int
    skipped: int
