;;; metacircular.em -- a Lisp interpreter written in Ember. Lisp in Lisp!
;;;
;;; m-eval understands numbers, symbols, quote, if, lambda, and application.
;;; Environments are association lists of (name value) pairs, so everything
;;; is purely functional -- which means recursion inside the interpreted
;;; language has to come from the Z combinator instead of `define`.

;; ---- environments ---------------------------------------------------------

(define (env-lookup name env)
  (let ((hit (assoc name env)))
    (if hit
        (cadr hit)
        (error "meta: unbound symbol" name))))

(define (env-extend names vals env)
  (if (null? names)
      env
      (cons (list (car names) (car vals))
            (env-extend (cdr names) (cdr vals) env))))

;; ---- eval / apply ---------------------------------------------------------

(define (m-eval x env)
  (cond ((number? x) x)
        ((string? x) x)
        ((symbol? x) (env-lookup x env))
        ((eq? (car x) 'quote)  (cadr x))
        ((eq? (car x) 'if)     (if (m-eval (cadr x) env)
                                   (m-eval (caddr x) env)
                                   (m-eval (cadddr x) env)))
        ((eq? (car x) 'lambda) (list 'closure (cadr x) (caddr x) env))
        (else (m-apply (m-eval (car x) env)
                       (map (lambda (a) (m-eval a env)) (cdr x))))))

(define (m-apply f args)
  (if (and (pair? f) (eq? (car f) 'closure))
      (m-eval (caddr f)                         ; closure body
              (env-extend (cadr f) args (cadddr f)))
      (apply f args)))                          ; host (Ember) builtin

;; ---- a base environment exposing a few Ember builtins ---------------------

(define base-env
  (list (list '+ +) (list '- -) (list '* *) (list '/ /)
        (list '= =) (list '< <) (list '> >)
        (list 'car car) (list 'cdr cdr) (list 'cons cons)
        (list 'null? null?) (list 'list list)))

;; ---- demos ----------------------------------------------------------------

(println "1. simple arithmetic, evaluated by the meta-evaluator:")
(println "   (* (+ 2 3) 7)           =>"
         (m-eval '(* (+ 2 3) 7) base-env))

(println "2. closures work (make-adder):")
(println "   (((lambda (n) (lambda (m) (+ n m))) 40) 2)  =>"
         (m-eval '(((lambda (n) (lambda (m) (+ n m))) 40) 2) base-env))

(println "3. quote:")
(println "   (car (quote (hello world)))  =>"
         (m-eval '(car (quote (hello world))) base-env))

;; Recursion without define: the Z combinator (call-by-value Y combinator).
(define Z
  '(lambda (f)
     ((lambda (x) (f (lambda (v) ((x x) v))))
      (lambda (x) (f (lambda (v) ((x x) v)))))))

(define fact-program
  (list (list Z '(lambda (fact)
                   (lambda (n)
                     (if (= n 0)
                         1
                         (* n (fact (- n 1)))))))
        10))

(println "4. factorial via the Z combinator, inside Lisp-in-Lisp:")
(println "   (fact 10)  =>" (m-eval fact-program base-env))

(define fib-program
  (list (list Z '(lambda (fib)
                   (lambda (n)
                     (if (< n 2)
                         n
                         (+ (fib (- n 1)) (fib (- n 2)))))))
        15))

(println "5. fibonacci the same way:")
(println "   (fib 15)   =>" (m-eval fib-program base-env))
