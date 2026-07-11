#!/usr/bin/env python3
"""Test suite for Ember. Run:  python3 tests.py"""

import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ember
from ember import Symbol, Keyword, EmberError, ParseError

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def ev(src, env=None):
    if env is None:
        env = ember.make_global_env()
    return ember.eval_string(src, env)


def capture(src, env=None):
    """Evaluate src and return what it printed to stdout."""
    if env is None:
        env = ember.make_global_env()
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        ember.eval_string(src, env)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old


def raises(exc, src):
    try:
        ev(src)
    except exc:
        return True
    except Exception as e:
        raise AssertionError("expected %s, got %r" % (exc.__name__, e))
    raise AssertionError("expected %s, got no error" % exc.__name__)


# ---------------------------------------------------------------------------
# Reader / parser
# ---------------------------------------------------------------------------

@test
def parse_numbers():
    assert ember.parse_all("42") == [42]
    assert ember.parse_all("-17") == [-17]
    assert ember.parse_all("+3") == [3]
    assert ember.parse_all("3.25") == [3.25]
    assert ember.parse_all("-2.5e3") == [-2500.0]
    assert ember.parse_all(".5") == [0.5]
    # things that look number-ish but aren't stay symbols
    assert ember.parse_all("x1") == [Symbol("x1")]
    assert ember.parse_all("-") == [Symbol("-")]
    assert ember.parse_all("1+") == [Symbol("1+")]


@test
def parse_strings_and_escapes():
    assert ember.parse_all('"hello"') == ["hello"]
    assert ember.parse_all(r'"a\nb\t\"q\"\\"') == ['a\nb\t"q"\\']
    assert raises(ParseError, '"unterminated')
    assert raises(ParseError, r'"bad \x escape"')


@test
def parse_symbols_keywords_bools():
    forms = ember.parse_all("foo :bar #t #f nil")
    assert forms[0] == Symbol("foo") and isinstance(forms[0], Symbol)
    assert forms[1] == Keyword(":bar") and isinstance(forms[1], Keyword)
    assert forms[2] is True and forms[3] is False
    assert forms[4] == []


@test
def parse_lists_and_nesting():
    assert ember.parse_all("(+ 1 (* 2 3))") == \
        [[Symbol("+"), 1, [Symbol("*"), 2, 3]]]
    assert raises(ParseError, "(1 2")
    assert raises(ParseError, ")")


@test
def parse_quote_sugar():
    assert ember.parse_all("'x") == [[Symbol("quote"), Symbol("x")]]
    assert ember.parse_all("`(a ,b ,@c)") == [[
        Symbol("quasiquote"),
        [Symbol("a"), [Symbol("unquote"), Symbol("b")],
         [Symbol("unquote-splicing"), Symbol("c")]]]]


@test
def parse_comments():
    assert ember.parse_all("; a comment\n1 ; trailing\n;; more") == [1]


@test
def balanced_depth_detection():
    assert ember.balanced_depth("(+ 1 2)") == 0
    assert ember.balanced_depth("(define (f x)") == 1
    assert ember.balanced_depth("(let ((a 1)") == 2
    assert ember.balanced_depth('(display "(((")') == 0   # parens in strings
    assert ember.balanced_depth('(display "open') > 0     # open string
    assert ember.balanced_depth("(f) ; comment (((") == 0  # parens in comments


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

@test
def arithmetic():
    assert ev("(+ 1 2 3)") == 6
    assert ev("(- 10 1 2)") == 7
    assert ev("(- 5)") == -5
    assert ev("(* 2 3 4)") == 24
    assert ev("(/ 6 3)") == 2          # exact int division stays int
    assert ev("(/ 1 2)") == 0.5
    assert ev("(mod 7 3)") == 1
    assert ev("(expt 2 10)") == 1024
    assert ev("(min 3 1 2)") == 1 and ev("(max 3 1 2)") == 3
    assert raises(EmberError, "(/ 1 0)")
    assert raises(EmberError, '(+ 1 "two")')


@test
def comparisons_and_equality():
    assert ev("(< 1 2 3)") is True
    assert ev("(< 1 3 2)") is False
    assert ev("(>= 3 3 2)") is True
    assert ev("(= 2 2 2)") is True
    assert ev("(equal? '(1 (2 3)) '(1 (2 3)))") is True
    assert ev("(equal? \"abc\" \"abc\")") is True
    assert ev("(eq? 'a 'a)") is True
    assert ev("(eq? 'a 'b)") is False
    assert ev("(not #f)") is True
    assert ev("(not '())") is True     # nil is falsy
    assert ev("(not 0)") is False      # 0 is truthy


@test
def special_forms_if_cond_and_or():
    assert ev("(if (> 2 1) 'yes 'no)") == Symbol("yes")
    assert ev("(if #f 'yes)") == []
    assert ev("""(cond ((= 1 2) 'a)
                       ((= 1 1) 'b)
                       (else 'c))""") == Symbol("b")
    assert ev("(cond (#f 1))") == []
    assert ev("(cond (42))") == 42          # test-only clause returns test
    assert ev("(and 1 2 3)") == 3
    assert ev("(and 1 #f 3)") is False
    assert ev("(and)") is True
    assert ev("(or #f nil 7)") == 7
    assert ev("(or #f #f)") is False
    # short-circuit: the (error) must never run
    assert ev("(or 1 (error \"boom\"))") == 1
    assert ev("(and #f (error \"boom\"))") is False


@test
def let_and_let_star():
    assert ev("(let ((a 1) (b 2)) (+ a b))") == 3
    assert ev("(let* ((a 1) (b (+ a 1))) (* a b))") == 2
    # let is parallel: inner b sees outer a
    assert ev("(define a 10) (let ((a 1) (b a)) b)") == 10


@test
def define_set_begin_while():
    env = ember.make_global_env()
    assert ev("(define x 5) x", env) == 5
    assert ev("(set! x 6) x", env) == 6
    assert raises(EmberError, "(set! never-defined 1)")
    assert ev("(begin 1 2 3)") == 3
    assert ev("""(define n 0)
                 (while (< n 5) (set! n (+ n 1)))
                 n""") == 5


@test
def closures_and_lexical_scope():
    env = ember.make_global_env()
    ev("""(define (make-counter)
            (let ((n 0))
              (lambda () (set! n (+ n 1)) n)))
          (define c1 (make-counter))
          (define c2 (make-counter))""", env)
    assert ev("(c1)", env) == 1
    assert ev("(c1)", env) == 2
    assert ev("(c2)", env) == 1       # independent closure state
    assert ev("(c1)", env) == 3
    # lexical, not dynamic, scoping:
    assert ev("""(define x 'global)
                 (define (get-x) x)
                 (define (shadowing) (let ((x 'local)) (get-x)))
                 (shadowing)""") == Symbol("global")


@test
def variadic_lambdas():
    assert ev("((lambda args args) 1 2 3)") == [1, 2, 3]
    assert ev("(define (f a . rest) (list a rest)) (f 1 2 3)") == [1, [2, 3]]
    assert ev("(define (f a . rest) (list a rest)) (f 1)") == [1, []]
    assert raises(EmberError, "(define (f a . rest) rest) (f)")
    assert raises(EmberError, "((lambda (a b) a) 1)")  # arity error


@test
def tail_call_optimization():
    # 200k tail-recursive calls: would need 200k Python stack frames
    # without TCO (Python's limit is ~20k here), so passing proves the
    # evaluator loops instead of recursing.
    assert ev("""(define (count n acc)
                   (if (= n 0) acc (count (- n 1) (+ acc 1))))
                 (count 200000 0)""") == 200000
    # mutual tail recursion is also safe
    assert ev("""(define (my-even? n) (if (= n 0) #t (my-odd? (- n 1))))
                 (define (my-odd? n) (if (= n 0) #f (my-even? (- n 1))))
                 (my-even? 100001)""") is False
    # ...and tail calls through cond / let / and / or / begin
    assert ev("""(define (down n)
                   (cond ((= n 0) 'done)
                         (else (let ((m (- n 1)))
                                 (and #t (or #f (begin (down m))))))))
                 (down 100000)""") == Symbol("done")


@test
def quasiquote_and_splicing():
    assert ev("`(1 ,(+ 1 1) ,@(list 3 4) 5)") == [1, 2, 3, 4, 5]
    assert ev("`(a b)") == [Symbol("a"), Symbol("b")]
    # nested quasiquote: inner level is preserved
    assert ev("`(1 `(2 ,(+ 1 2)))") == \
        [1, [Symbol("quasiquote"), [2, [Symbol("unquote"),
                                        [Symbol("+"), 1, 2]]]]]
    assert ev("(define x 9) `(a `(b ,,x))") == \
        [Symbol("a"), [Symbol("quasiquote"),
                       [Symbol("b"), [Symbol("unquote"), 9]]]]
    assert raises(EmberError, ",x")
    assert raises(EmberError, "`(1 ,@2)")  # splicing a non-list


@test
def macros_defmacro():
    env = ember.make_global_env()
    ev("""(defmacro my-if2 (c a b) `(cond (,c ,a) (else ,b)))""", env)
    assert ev("(my-if2 (> 2 1) 'yes 'no)", env) == Symbol("yes")
    # macro args are NOT evaluated before expansion
    ev("(defmacro second-form (a b) b)", env)
    assert ev("(second-form (error \"never runs\") 42)", env) == 42
    # macroexpand-1 helper
    form = ember.parse_all("(when #t 1 2)")[0]
    expansion, did = ember.macroexpand_1(form, env)
    assert did
    assert expansion == ember.parse_all("(if #t (begin 1 2) nil)")[0]


@test
def prelude_macros():
    assert ev("(when (> 2 1) 1 2 3)") == 3
    assert ev("(when (< 2 1) 1 2 3)") == []
    assert ev("(unless (< 2 1) 'ran)") == Symbol("ran")
    assert ev("(unless (> 2 1) 'ran)") == []
    # threading macro
    assert ev("(-> 5 (+ 3) (* 2))") == 16
    assert ev("(-> 16 sqrt)") == 4.0
    assert ev("""(-> "a,b,c" (string-split ",") (string-join "-"))""") == "a-b-c"
    assert ev("(-> 10)") == 10
    # for loop macro (built on let/while/set! + gensym)
    assert ev("""(define total 0)
                 (for (i 0 5) (set! total (+ total i)))
                 total""") == 10
    # loop variable is scoped to the loop; outer i is untouched
    assert ev("""(define i 'outer)
                 (for (i 0 3) i)
                 i""") == Symbol("outer")
    # swap!
    assert ev("(define n 10) (swap! n (lambda (v) (* v v))) n") == 100


@test
def list_builtins():
    assert ev("(cons 1 '(2 3))") == [1, 2, 3]
    assert ev("(car '(1 2 3))") == 1
    assert ev("(cdr '(1 2 3))") == [2, 3]
    assert ev("(append '(1) '(2 3) '())") == [1, 2, 3]
    assert ev("(reverse '(1 2 3))") == [3, 2, 1]
    assert ev("(length '(a b c))") == 3
    assert ev("(range 5)") == [0, 1, 2, 3, 4]
    assert ev("(range 2 5)") == [2, 3, 4]
    assert ev("(range 10 0 -3)") == [10, 7, 4, 1]
    assert ev("(nth '(a b c) 1)") == Symbol("b")
    assert ev("(take 2 '(1 2 3))") == [1, 2]
    assert ev("(drop 2 '(1 2 3))") == [3]
    assert ev("(member 2 '(1 2 3))") == [2, 3]
    assert ev("(member 9 '(1 2 3))") is False
    assert ev("(assoc 'b '((a 1) (b 2)))") == [Symbol("b"), 2]
    assert ev("(assoc 'z '((a 1)))") is False
    assert ev("(sort '(3 1 2))") == [1, 2, 3]
    assert ev("(sort '(1 2 3) >)") == [3, 2, 1]
    assert ev("(zip '(1 2) '(a b))") == [[1, Symbol("a")], [2, Symbol("b")]]
    assert raises(EmberError, "(car '())")
    assert raises(EmberError, "(cons 1 2)")   # no improper pairs


@test
def higher_order_builtins():
    assert ev("(map (lambda (x) (* x x)) '(1 2 3))") == [1, 4, 9]
    assert ev("(map + '(1 2) '(10 20))") == [11, 22]
    assert ev("(filter odd? (range 10))") == [1, 3, 5, 7, 9]
    assert ev("(reduce + 0 (range 101))") == 5050
    assert ev("(reduce (lambda (acc x) (cons x acc)) '() '(1 2 3))") == [3, 2, 1]
    assert ev("(apply + '(1 2 3))") == 6
    assert ev("(apply max '(3 9 4))") == 9
    assert ev("((compose (lambda (x) (* 2 x)) +) 1 2 3)") == 12
    assert ev("(any? even? '(1 3 4))") is True
    assert ev("(all? even? '(2 4 6))") is True
    assert ev("(sum '(1 2 3 4))") == 10
    assert ev("(product '(1 2 3 4))") == 24


@test
def string_builtins():
    assert ev('(string-append "foo" "bar")') == "foobar"
    assert ev('(string-length "hello")') == 5
    assert ev('(substring "hello" 1 3)') == "el"
    assert ev('(string-upcase "abc")') == "ABC"
    assert ev('(string-split "a b c" " ")') == ["a", "b", "c"]
    assert ev('(string-join (list "a" "b") "+")') == "a+b"
    assert ev('(string->number "42")') == 42
    assert ev('(string->number "2.5")') == 2.5
    assert ev('(string->number "nope")') is False
    assert ev('(number->string 42)') == "42"
    assert ev("(symbol->string 'abc)") == "abc"
    assert isinstance(ev('(string->symbol "abc")'), Symbol)
    assert ev('(string-ref "abc" 1)') == "b"
    assert ev('(str "n=" 42 " l=" (list 1 2))') == "n=42 l=(1 2)"
    assert ev('(string-contains? "hello" "ell")') is True


@test
def type_predicates():
    assert ev("(number? 3)") is True
    assert ev("(number? #t)") is False        # booleans are not numbers
    assert ev('(string? "s")') is True
    assert ev("(string? 's)") is False        # symbols are not strings
    assert ev("(symbol? 's)") is True
    assert ev("(keyword? :k)") is True
    assert ev("(null? '())") is True
    assert ev("(pair? '(1))") is True
    assert ev("(pair? '())") is False
    assert ev("(procedure? car)") is True
    assert ev("(procedure? (lambda (x) x))") is True


@test
def keywords_self_evaluate():
    assert ev(":foo") == Keyword(":foo")
    assert ev("(list :a 1 :b 2)") == [Keyword(":a"), 1, Keyword(":b"), 2]


@test
def eval_and_read_string():
    assert ev("(eval '(+ 1 2))") == 3
    assert ev('(eval (read-string "(* 6 7)"))') == 42


@test
def output_and_printing():
    assert capture('(display "a" "b") (newline) (println "x" 42)') == "ab\nx 42\n"
    assert capture("(println '(1 \"two\" three))") == '(1 two three)\n'
    env = ember.make_global_env()
    assert ember.to_string(ev("'(1 \"two\" (3))", env)) == '(1 "two" (3))'
    assert ember.to_string(ev("''x", env)) == "'x"
    assert ember.to_string(3.5) == "3.5"
    assert ember.to_string(True) == "#t"


@test
def error_messages_are_readable():
    for src, fragment in [
        ("undefined-thing", "unbound symbol 'undefined-thing'"),
        ("(car 5)", "car"),
        ("((lambda (x) x) 1 2)", "expected 1 argument, got 2"),
        ('("hello" 1)', "not a procedure"),
    ]:
        try:
            ev(src)
            raise AssertionError("expected error for %s" % src)
        except EmberError as e:
            assert fragment in str(e), "%r not in %r" % (fragment, str(e))


@test
def gensym_is_fresh():
    env = ember.make_global_env()
    a = ev("(gensym)", env)
    b = ev("(gensym)", env)
    assert isinstance(a, Symbol) and a != b


# ---------------------------------------------------------------------------
# Examples run end-to-end
# ---------------------------------------------------------------------------

def run_example(name):
    path = os.path.join(HERE, "examples", name)
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "ember.py"), path],
        capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, "%s failed:\n%s" % (name, proc.stderr)
    return proc.stdout


@test
def example_metacircular():
    out = run_example("metacircular.em")
    assert "35" in out                    # (* (+ 2 3) 7)
    assert "42" in out                    # make-adder
    assert "hello" in out                 # quote demo
    assert "3628800" in out               # fact 10 via Z combinator
    assert "610" in out                   # fib 15


@test
def example_diff():
    out = run_example("diff.em")
    assert "(+ (+ x x) 3)" in out         # d/dx (x^2 + 3x)
    assert "(* 5 (expt x 4))" in out      # power rule
    assert "13" in out                    # derivative evaluated at x=5


@test
def example_mandelbrot():
    out = run_example("mandelbrot.em")
    lines = out.strip().split("\n")
    art = [l for l in lines if "@" in l]
    assert len(art) >= 10, "expected a picture with interior points"
    assert any(len(l) >= 60 for l in art)
    assert "done:" in out


# ---------------------------------------------------------------------------

def main():
    failures = 0
    for fn in TESTS:
        try:
            fn()
            print("ok   %s" % fn.__name__)
        except Exception as e:
            failures += 1
            print("FAIL %s: %s" % (fn.__name__, e))
    print()
    if failures:
        print("%d/%d tests FAILED" % (failures, len(TESTS)))
        return 1
    print("All %d tests passed." % len(TESTS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
