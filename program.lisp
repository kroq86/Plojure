; Testing define, list, and print
(define x (list 1 2 3))
(print "Defined x:" x)

; Testing append
(define y (append x (list 4 5)))
(print "Appended y:" y)

; Testing arithmetic operators
(define z (+ (* 2 3) (- 10 4)))
(print "Arithmetic result z:" z)

; Testing if
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

; Testing car, cdr, cons
(print "First element of x" (car x)) ; This is correct
; Correct usage of cdr
(print "Rest of x:" (cdr x)) ; Assuming x is defined and is a list
(print "Adding element with cons:" (cons 0 x))

; Testing map with lambda
(print "Square of all elements in x:" (map (lambda (n) (* n n)) x))

; Testing filter
(print "Filtering odd numbers from x:" (filter (lambda (n) (% n 2)) x))

; Testing nested let
(let ((a 5) (b 10))
  (let ((c (+ a b)))
    (print "Nested let c:" c)))
