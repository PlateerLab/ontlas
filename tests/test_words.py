from ontlas.words import fix, josa


def test_a_particle_follows_the_word_before_it():
    assert [josa(w, "을") for w in ("주문", "고객", "카테고리", "Order", "Item", "Plan", "Sku", "SQL", "API", "C1", "3")] == \
        ["을", "을", "를", "를", "을", "을", "를", "을", "를", "을", "을"]
    assert [josa(w, "으로") for w in ("배송", "서울", "Order", "Item", "Model", "5")] == ["으로", "로", "로", "으로", "로", "로"]
    assert josa("'Customer'", "이") == "가" and josa("(주문)", "은") == "은"


def test_a_sentence_loses_its_held_particles():
    assert fix("용어 '배송완료'을(를) 찾지 못했습니다.") == "용어 '배송완료'를 찾지 못했습니다."
    assert fix("Object Order이(가) 이미 있습니다. 값은 VIP(으)로 정했습니다.") == "Object Order가 이미 있습니다. 값은 VIP로 정했습니다."
    assert fix("괄호 없는 문장") == "괄호 없는 문장"
