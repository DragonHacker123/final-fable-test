# Ember

A small, complete Lisp dialect implemented in pure Python — standard library
only, no dependencies. Ember has a proper reader, lexical closures,
tail-call optimization, and real macros powerful enough that `when`,
`unless`, `->`, and `for` are all defined *in Ember itself* (see
[`prelude.em`](prelude.em)).

```
ember-lisp/
├── ember.py            the interpreter: reader, evaluator, builtins
├── prelude.em          Ember's standard prelude, written in Ember
├── repl.py             interactive REPL with multi-line input
├── tests.py            test suite (python3 tests.py)
└── examples/
    ├── metacircular.em Lisp-in-Lisp: a meta-evaluator, with Z-combinator recursion
    ├── diff.em         symbolic differentiator with simplification
    └── mandelbrot.em   ASCII Mandelbrot (floats + TCO + the `for` macro)
```

## Quick start

```sh
python3 repl.py                        # interactive REPL
python3 ember.py examples/mandelbrot.em  # run a program
python3 tests.py                       # run the test suite
```

## Language tour

### Data types

| Syntax                  | Type                                       |
|-------------------------|--------------------------------------------|
| `42`, `-17`, `3.5e2`    | integers and floats                        |
| `"hi\nthere"`           | strings, with `\n \t \r \" \\ \0` escapes  |
| `foo`, `+`, `list->vec` | symbols                                    |
| `:name`                 | keywords (self-evaluating)                 |
| `#t`, `#f`              | booleans                                   |
| `nil`, `'()`            | the empty list                             |
| `(1 "two" three)`       | lists                                      |

Only `#f` and `nil` are falsy — `0` and `""` are truthy.
Comments run from `;` to end of line.

### Special forms

```lisp
(define x 10)                       ; bind a variable
(define (square x) (* x x))         ; function shorthand
(lambda (a b) (+ a b))              ; anonymous function
(lambda (a . rest) rest)            ; variadic: rest is a list
(lambda args args)                  ; collect ALL args as a list
(if test then else)                 ; else is optional
(cond (test expr...) ... (else e))  ; multi-way branch
(let ((a 1) (b 2)) body...)         ; parallel bindings
(let* ((a 1) (b (+ a 1))) body...)  ; sequential bindings
(set! x 99)                         ; mutate an existing binding
(begin e1 e2 e3)                    ; sequence, returns last
(and a b c)  (or a b c)             ; short-circuiting
(while test body...)                ; imperative loop
(quote x)   'x                      ; don't evaluate
(quasiquote ...)  `(a ,b ,@cs)      ; templates with unquote / splicing
(defmacro name (params) body...)    ; define a macro
```

### Closures and lexical scope

```lisp
(define (make-counter)
  (let ((n 0))
    (lambda () (set! n (+ n 1)) n)))

(define c (make-counter))
(c)  ; => 1
(c)  ; => 2   -- each counter has its own private n
```

### Tail-call optimization

The evaluator is a loop, not a recursive function, so tail calls —
including mutual tail calls, and tail positions inside `if`, `cond`, `let`,
`begin`, `and`, and `or` — consume no stack:

```lisp
(define (count n acc)
  (if (= n 0) acc (count (- n 1) (+ acc 1))))

(count 200000 0)  ; => 200000, no stack overflow
```

Without TCO this would need 200,000 Python stack frames; the test suite
verifies it runs fine.

### Macros

`defmacro` receives its arguments *unevaluated* and returns code.
Quasiquote makes templates readable. The entire "control-flow extension"
layer of Ember is bootstrapped this way in `prelude.em`:

```lisp
(defmacro when (test . body)
  `(if ,test (begin ,@body) nil))

(defmacro for (spec . body)              ; (for (i 0 10) ...)
  (let ((var   (car spec))
        (start (cadr spec))
        (limit (gensym "for-end")))      ; hygiene via gensym
    `(let ((,var ,start)
           (,limit ,(caddr spec)))
       (while (< ,var ,limit)
         ,@body
         (set! ,var (+ ,var 1))))))
```

The thread-first macro `->` (as in Clojure) is also a prelude macro:

```lisp
(-> 5 (+ 3) (* 2))                        ; => 16, i.e. (* (+ 5 3) 2)
(-> "a,b,c" (string-split ",") (string-join "-"))  ; => "a-b-c"
```

### Builtin library (selection)

- **arithmetic** — `+ - * /` (variadic), `mod quotient remainder abs min max
  floor ceiling round sqrt expt exp log sin cos tan even? odd? zero?`
- **comparison** — `= < > <= >=` (chained: `(< 1 2 3)`), `equal? eq? not`
- **lists** — `cons car cdr list length append reverse nth first rest last
  take drop range member assoc sort zip null? pair? list?`
- **higher-order** — `map` (multi-list), `filter reduce apply for-each`,
  plus `compose sum product any? all?` from the prelude
- **strings** — `str string-append string-length substring string-ref
  string-upcase string-downcase string-split string-join string-contains?
  string->number number->string string->symbol symbol->string string->list`
- **predicates** — `number? integer? float? string? symbol? keyword?
  boolean? procedure?`
- **misc** — `display println newline error gensym eval read-string`

## Sample REPL session

```
$ python3 repl.py
Ember 1.0 -- a small Lisp in pure Python

ember> (+ 1 2 3)
=> 6
ember> (define (fib n)
  ...>   (if (< n 2)
  ...>       n
  ...>       (+ (fib (- n 1)) (fib (- n 2)))))
=> fib
ember> (map fib (range 10))
=> (0 1 1 2 3 5 8 13 21 34)
ember> (-> 5 (+ 3) (* 2))
=> 16
ember> (filter odd? (range 10))
=> (1 3 5 7 9)
ember> `(1 ,(+ 1 1) ,@(list 3 4))
=> (1 2 3 4)
ember> (defmacro square-of (e) `(* ,e ,e))
=> square-of
ember> (square-of 12)
=> 144
ember> (car '())
error: car: expected a non-empty list, got ()
ember> undefined-thing
error: unbound symbol 'undefined-thing'
```

## Showcase examples

- **`examples/metacircular.em`** — a metacircular evaluator: a Lisp
  interpreter written in Ember, complete with closures and quoting. Since
  its environments are immutable association lists, recursion in the
  interpreted language comes from the **Z combinator** — it computes
  `(fact 10)` and `(fib 15)` without ever using `define`.
- **`examples/diff.em`** — symbolic differentiation with algebraic
  simplification (`d/dx (x² + 3x)` → `(+ (+ x x) 3)`), then numerically
  evaluates a derivative using Ember's `eval`.
- **`examples/mandelbrot.em`** — renders the Mandelbrot set as ASCII art
  using the `for` macro, float math, and a deeply tail-recursive
  escape-time loop.

## Design notes

- Lists are Python lists (no improper/dotted pairs — `cons` requires a
  list tail). The dotted syntax is reserved for variadic parameter lists.
- `/` keeps integers exact when the division is exact: `(/ 6 3)` → `2`,
  `(/ 1 2)` → `0.5`.
- `define` returns the defined symbol, which is what the REPL prints.
- Macros are expanded at call time by the evaluator; `gensym` is available
  for writing capture-free templates.
