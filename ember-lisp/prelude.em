;;; prelude.em -- Ember's standard prelude, written in Ember itself.
;;; Loaded automatically into every global environment.

;; ---- list accessors ------------------------------------------------------

(define (caar l)   (car (car l)))
(define (cadr l)   (car (cdr l)))
(define (cddr l)   (cdr (cdr l)))
(define (caddr l)  (car (cddr l)))
(define (cadddr l) (car (cdr (cddr l))))
(define (second l) (cadr l))
(define (third l)  (caddr l))

;; ---- small function utilities -------------------------------------------

(define (identity x) x)

(define (compose f g)
  (lambda args (f (apply g args))))

(define (const x)
  (lambda ignored x))

(define (sum lst)     (reduce + 0 lst))
(define (product lst) (reduce * 1 lst))

;; any?/all? over a predicate
(define (any? pred lst)
  (cond ((null? lst) #f)
        ((pred (car lst)) #t)
        (else (any? pred (cdr lst)))))

(define (all? pred lst)
  (cond ((null? lst) #t)
        ((pred (car lst)) (all? pred (cdr lst)))
        (else #f)))

;; ---- macros ---------------------------------------------------------------
;; These are the showcase: real macros, defined with defmacro and
;; quasiquote templates, in Ember source code.

;; (when test body...) => evaluate body only if test is truthy
(defmacro when (test . body)
  `(if ,test (begin ,@body) nil))

;; (unless test body...) => evaluate body only if test is falsy
(defmacro unless (test . body)
  `(if ,test nil (begin ,@body)))

;; (-> x (f a b) g ...) -- thread-first macro, as in Clojure.
;; (-> 5 (+ 3) (* 2))  expands to  (* (+ 5 3) 2)
(defmacro -> (x . forms)
  (if (null? forms)
      x
      (let ((form (car forms)))
        (let ((threaded (if (pair? form)
                            (cons (car form) (cons x (cdr form)))
                            (list form x))))
          (cons '-> (cons threaded (cdr forms)))))))

;; (for (i start end) body...) -- a counting loop built from let/while/set!.
;; Uses gensym so the end-expression is evaluated once and can't capture
;; user variables.
(defmacro for (spec . body)
  (let ((var   (car spec))
        (start (cadr spec))
        (limit (gensym "for-end")))
    `(let ((,var ,start)
           (,limit ,(caddr spec)))
       (while (< ,var ,limit)
         ,@body
         (set! ,var (+ ,var 1))))))

;; (swap! name f) => (set! name (f name)) -- tiny bonus macro
(defmacro swap! (name f)
  `(set! ,name (,f ,name)))
