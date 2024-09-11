; Fibonacci function
(define fib (lambda (n)
  (cond ((eq n 0) 0)
        ((eq n 1) 1)
        (t (+ (fib (- n 1)) (fib (- n 2)))))))

; Print first 10 Fibonacci numbers
(print "First 10 Fibonacci numbers:")
(define print-fib (lambda (n)
  (cond ((eq n 0) (print))
        (t (begin
             (print (fib (- n 1)))
             (print-fib (- n 1)))))))
(print-fib 10)

; Prime number checker
(define is-prime (lambda (n)
  (define check-prime (lambda (i)
    (cond ((eq i n) t)
          ((eq (% n i) 0) nil)
          (t (check-prime (+ i 1))))))
  (cond ((< n 2) nil)
        (t (check-prime 2)))))

; Print prime numbers up to 20
(print "Prime numbers up to 20:")
(define print-primes (lambda (n)
  (cond ((< n 2) (print))
        (t (begin
             (cond ((is-prime n) (print n)))
             (print-primes (- n 1)))))))
(print-primes 20)