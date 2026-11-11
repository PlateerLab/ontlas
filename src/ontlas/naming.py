"""English API names for what a draft finds under Korean names.

A table called 주문상태이력 should become OrderStatusHistory, not Jumunsangtaeiryeok. The words come from what the
library already says (a standard object named 주문 is Order), from the glossaries (회원 is 고객), then from a short list
of words data tables are made of. A name is only offered when every part of the Korean name is a known word;
otherwise the romanized name stays, and the page asks a person to name it.
"""
from __future__ import annotations

import re

# words tables and columns are made of, for what no module names
BASE = {
    "이력": "History", "내역": "Detail", "기록": "Record", "상태": "Status", "번호": "No", "코드": "Code", "이름": "Name",
    "명": "Name", "일시": "At", "일자": "Date", "날짜": "Date", "시각": "Time", "금액": "Amount", "수량": "Quantity",
    "회원": "Member", "고객": "Customer", "주소": "Address", "연락처": "Phone", "전화": "Phone", "이메일": "Email",
    "등급": "Grade", "유형": "Type", "구분": "Kind", "분류": "Category", "상세": "Detail", "정보": "Info", "목록": "List",
    "대상": "Target", "사유": "Reason", "요청": "Request", "처리": "Process", "결과": "Result", "변경": "Change",
    "가격": "Price", "재고": "Stock", "매장": "Store", "지점": "Branch", "직원": "Employee", "부서": "Department",
    "계약": "Contract", "청구": "Billing", "정산": "Settlement", "리뷰": "Review", "후기": "Review", "문의": "Inquiry",
    "답변": "Answer", "공지": "Notice", "댓글": "Comment", "카드": "Card", "계좌": "Account", "거래": "Transaction",
    "대출": "Loan", "도서": "Book", "저자": "Author", "출판사": "Publisher", "학생": "Student", "강의": "Course",
    "수강": "Enrollment", "환자": "Patient", "진료": "Visit", "의사": "Doctor", "예약": "Reservation", "일정": "Schedule",
    "차량": "Vehicle", "기사": "Driver", "창고": "Warehouse", "입고": "Inbound", "출고": "Outbound", "발주": "PurchaseOrder",
    "공급사": "Supplier", "품목": "Item", "제품": "Product", "상품": "Product", "주문": "Order", "배송": "Shipment",
    "결제": "Payment", "판매자": "Seller", "구매자": "Buyer", "사용자": "User", "회사": "Company", "고객사": "Client",
    "프로젝트": "Project", "작업": "Task", "문서": "Document", "파일": "File", "로그": "Log", "이벤트": "Event",
    "쿠폰": "Coupon", "포인트": "Point", "캠페인": "Campaign", "장바구니": "Cart", "반품": "Return", "교환": "Exchange",
    "환불": "Refund", "취소": "Cancellation", "카테고리": "Category", "브랜드": "Brand", "옵션": "Option", "단품": "Sku",
    "택배사": "Carrier", "송장": "Invoice", "할인": "Discount", "적립": "Reward", "멤버십": "Membership", "구독": "Subscription",
    "센터": "Center", "담당자": "Manager", "사원": "Employee", "급여": "Payroll", "근태": "Attendance", "설비": "Equipment",
    "점검": "Inspection", "생산": "Production", "공정": "Process", "라인": "Line", "불량": "Defect", "품질": "Quality",
    "완료": "Complete", "배송완료": "Delivered", "발송": "Shipped", "배송중": "Shipped", "결제완료": "Paid", "입금": "Paid",
    "승인": "Approved", "거절": "Rejected", "반려": "Rejected", "대기": "Pending", "진행": "Progress", "활성": "Active",
}
_WORD = re.compile(r"[^0-9A-Za-z가-힣]+")


def _pascal(name: str) -> str:
    parts = [p for p in re.split(r"[_\W]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def vocabulary(ontologies=(), terms=()) -> dict[str, str]:
    """Korean word -> English word: the base list, then what modules name (their objects, and properties whose label
    and name have as many words), then the glossaries' synonyms, which read as the word they stand for."""
    out = dict(BASE)
    for onto in ontologies:
        for o in onto.objects.values():
            if o.label and re.search(r"[가-힣]", o.label):
                out[_WORD.sub("", o.label)] = _pascal(o.name)
            for p in o.properties.values():
                words, parts = (p.label or "").split(), [x for x in p.name.split("_") if x]
                if words and len(words) == len(parts) and all(re.search(r"[가-힣]", w) for w in words):
                    for w, x in zip(words, parts):
                        out.setdefault(_WORD.sub("", w), x[:1].upper() + x[1:])
    for t in terms:
        word = _WORD.sub("", str(t.get("term") or ""))
        if word not in out:
            continue
        for s in t.get("synonyms") or []:
            out.setdefault(_WORD.sub("", str(s)), out[word])
    return out


def english(label: str, vocab: dict[str, str]) -> tuple[str, list[list[str]]] | None:
    """The English name for a Korean label when every part of it is a known word: (name, [[part, word], ...]).
    The fewest parts win, so 주문상품 is one word when it is one, not 주문 + 상품."""
    text = _WORD.sub("", label or "")
    if not text or not re.search(r"[가-힣]", text):
        return None
    n = len(text)
    best: list[list[str] | None] = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for j in range(n, i, -1):
            part = text[i:j]
            word = vocab.get(part) or (part if re.fullmatch(r"[A-Za-z0-9]+", part) else None)
            if word and (best[j] is None or len(best[i]) + 1 < len(best[j])):
                best[j] = [*best[i], part]
    parts = best[n]
    if not parts:
        return None
    words = [vocab.get(p) or p for p in parts]
    out: list[str] = []
    for w in words:  # 주문 + 주문번호 should not say Order twice
        if not out or out[-1] != w:
            out.append(w)
    name = "".join(w[:1].upper() + w[1:] for w in out)
    return (name if not name[0].isdigit() else f"N{name}"), [[p, vocab.get(p) or p] for p in parts]


def stem(word: str) -> str:
    """An English word without the ending a code may drop or change: Cancellation is CANCELL, Delivered DELIVER."""
    w = word.upper()
    for end in ("ATION", "MENT", "ING", "ED", "S"):
        if len(w) > len(end) + 3 and w.endswith(end):
            return w[: -len(end)]
    return w


__all__ = ["BASE", "english", "stem", "vocabulary"]
