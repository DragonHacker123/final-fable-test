;;; mandelbrot.em -- ASCII Mandelbrot set.
;;;
;;; Shows off three things at once:
;;;   * the `for` macro from the prelude (defined in Ember, not Python)
;;;   * float arithmetic
;;;   * tail-call optimization: `iterate` is deeply tail-recursive and runs
;;;     thousands of times without touching the Python stack.

(define width    64)
(define height   22)
(define max-iter 24)
(define palette  " .:-=+*#%")

;; Escape-time iteration, written tail-recursively (TCO makes this a loop).
(define (iterate cx cy x y n)
  (if (or (= n max-iter)
          (> (+ (* x x) (* y y)) 4.0))
      n
      (iterate cx cy
               (+ (- (* x x) (* y y)) cx)
               (+ (* 2.0 x y) cy)
               (+ n 1))))

(define (pixel n)
  (if (= n max-iter)
      "@"
      (string-ref palette (remainder n 9))))

(println "The Mandelbrot set, rendered by Ember:")
(newline)

(for (py 0 height)
  (define row "")
  (for (px 0 width)
    (define cx (+ -2.2 (* px (/ 3.0 width))))
    (define cy (+ -1.2 (* py (/ 2.4 height))))
    (set! row (string-append row (pixel (iterate cx cy 0.0 0.0 0)))))
  (println row))

(newline)
(println "done:" (* width height) "points,"
         "max" max-iter "iterations each.")
