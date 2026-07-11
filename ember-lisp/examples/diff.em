;;; diff.em -- a tiny symbolic differentiator with algebraic simplification.
;;;
;;; Handles +, -, *, expt (power rule), sin, and cos over binary expressions,
;;; simplifying as it builds results:  (* 1 x) => x,  (+ 0 e) => e, and
;;; constant subexpressions are folded.

;; ---- smart constructors (simplify while building) --------------------------

(define (make-sum a b)
  (cond ((and (number? a) (number? b)) (+ a b))
        ((equal? a 0) b)
        ((equal? b 0) a)
        (else (list '+ a b))))

(define (make-diff a b)
  (cond ((and (number? a) (number? b)) (- a b))
        ((equal? b 0) a)
        (else (list '- a b))))

(define (make-product a b)
  (cond ((and (number? a) (number? b)) (* a b))
        ((or (equal? a 0) (equal? b 0)) 0)
        ((equal? a 1) b)
        ((equal? b 1) a)
        (else (list '* a b))))

(define (make-expt base n)
  (cond ((equal? n 0) 1)
        ((equal? n 1) base)
        (else (list 'expt base n))))

;; ---- the differentiator -----------------------------------------------------

(define (deriv e x)
  (cond ((number? e) 0)
        ((symbol? e) (if (eq? e x) 1 0))
        ((eq? (car e) '+)
         (make-sum (deriv (cadr e) x) (deriv (caddr e) x)))
        ((eq? (car e) '-)
         (make-diff (deriv (cadr e) x) (deriv (caddr e) x)))
        ((eq? (car e) '*)                                ; product rule
         (make-sum (make-product (cadr e) (deriv (caddr e) x))
                   (make-product (deriv (cadr e) x) (caddr e))))
        ((eq? (car e) 'expt)                             ; power rule
         (make-product
          (make-product (caddr e)
                        (make-expt (cadr e) (- (caddr e) 1)))
          (deriv (cadr e) x)))
        ((eq? (car e) 'sin)                              ; chain rule
         (make-product (list 'cos (cadr e)) (deriv (cadr e) x)))
        ((eq? (car e) 'cos)
         (make-product (make-product -1 (list 'sin (cadr e)))
                       (deriv (cadr e) x)))
        (else (error "deriv: unknown operator" (car e)))))

;; ---- demo -------------------------------------------------------------------

(define (show e x)
  (println "d/d" x " " e)
  (println "        = " (deriv e x))
  (newline))

(show '(+ (* x x) (* 3 x)) 'x)
(show '(expt x 5) 'x)
(show '(* (sin x) (cos x)) 'x)
(show '(+ (expt x 3) (- (* 7 x) 4)) 'x)
(show '(sin (* 2 x)) 'x)

;; And because expressions are just lists, we can evaluate the derivative
;; numerically with the `eval` builtin:
(define d (deriv '(+ (* x x) (* 3 x)) 'x))   ; => (+ (+ x x) 3)
(define at-5 (eval (list 'let '((x 5)) d)))
(println "value of " d " at x=5  =>  " at-5)
