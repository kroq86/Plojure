; Testing define, list, and print
(define x (list 1 2 3))
(print "Defined x:" x)

; Testing append
(define y (append x (list 4 5)))
(print "Appended y:" y)

; Testing arithmetic operators
(define z (+ (* 2 3) (- 10 4)))
(print "Arithmetic result z:" z)

; Testing if statement
(if (< z 20)
    (print "z is less than 20")
    (print "z is greater or equal to 20"))

; Testing let
(let ((a 10) (b 20))
  (print "Sum of a and b:" (+ a b)))

; Testing set!
(set! x (append x (list 6 7)))
(print "Updated x:" x)

; Testing lambda and function calls
(define square (lambda (n) (* n n)))
(print "Square of 5:" (square 5))

; Testing recursion with factorial
(define factorial
  (lambda (n)
    (if (eq n 0)
        1
        (* n (factorial (- n 1))))))
(print "Factorial of 5:" (factorial 5))

; Testing cond
(define number-type
  (lambda (n)
    (cond
      ((< n 0) "Negative")
      ((eq n 0) "Zero")
      (t "Positive"))))
(print "Number type of -10:" (number-type -10))
(print "Number type of 0:" (number-type 0))
(print "Number type of 10:" (number-type 10))

; Testing car, cdr, and cons
(print "First element of x:" (car x))
(print "Rest of x:" (cdr x))
(print "Adding element with cons:" (cons 0 x))

; Testing map with lambda
(print "Square of all elements in x:" (map (lambda (n) (* n n)) x))

; Testing filter
(print "Filtering odd numbers from x:" (filter (lambda (n) (% n 2)) x))

; Testing nested let
(let ((a 5) (b 10))
  (let ((c (+ a b)))
    (print "Nested let c:" c)))

; Testing recursion with power function
(define (power base exp)
  (if (eq exp 0)
      1
      (* base (power base (- exp 1)))))
(print "Result of power:" (power 2 3))

(define = eq)
(define plus +)
(define quotient /)
(define times *)
(define difference -)

(define power 
  (lambda (base exponent)
    (cond 
      ((eq exponent 0) 1)
      ((eq exponent 1) base)
      (t (times base (power base (difference exponent 1)))))))

(print "Testing power function:")
(power 2 3)  ; Should output 8

(define is-power-of-two
  (lambda (n)
    (cond
      ((< n 1) nil)
      ((eq n 1) t)
      ((eq (% n 2) 1) nil)
      (t (is-power-of-two (quotient n 2))))))

(print "Testing is-power-of-two:")
(is-power-of-two 8)  ; Should output t

(define log2
  (lambda (n)
    (cond
      ((< n 1) nil)
      ((eq n 1) 0)
      (t (plus 1 (log2 (quotient n 2)))))))

(print "Testing log2:")
(log2 8)  ; Should output 3
