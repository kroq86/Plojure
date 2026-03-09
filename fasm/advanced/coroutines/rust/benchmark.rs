use std::env;
use std::ffi::c_void;
use std::ptr;
use std::time::Instant;

#[repr(C)]
struct Generator {
    fresh: u8,
    dead: u8,
    padding: [u8; 6],
    rsp: *mut c_void,
    stack_base: *mut c_void,
    func: *mut c_void,
}

unsafe extern "C" {
    fn python_generator_init();
    fn python_generator_next(g: *mut Generator, arg: *mut c_void) -> *mut c_void;
    fn bench_coroutine_func(arg: *mut c_void);
}

fn main() {
    let iters: usize = env::args()
        .nth(1)
        .unwrap_or_else(|| "200000".to_string())
        .parse()
        .expect("iterations must be an integer");

    let stack_capacity = 1024 * 4096usize;

    unsafe { python_generator_init() };

    let mut stack = vec![0u8; stack_capacity].into_boxed_slice();
    let stack_ptr = stack.as_mut_ptr() as *mut c_void;

    let started = Instant::now();

    let mut g = Generator {
        fresh: 1,
        dead: 0,
        padding: [0; 6],
        rsp: ptr::null_mut(),
        stack_base: stack_ptr,
        func: bench_coroutine_func as *mut c_void,
    };

    let r1 = unsafe { python_generator_next(&mut g, ptr::null_mut()) };
    let r2 = unsafe { python_generator_next(&mut g, 42usize as *mut c_void) };
    let r3 = unsafe { python_generator_next(&mut g, 84usize as *mut c_void) };

    if r1.is_null() || r2.is_null() || !r3.is_null() {
        eprintln!("unexpected sequence: r1={:?} r2={:?} r3={:?}", r1, r2, r3);
        std::process::exit(4);
    }

    std::mem::forget(stack);

    let sec = started.elapsed().as_secs_f64();
    let ops = 1.0 / sec;
    println!(
        "lang=rust,iters=1,total_sec={:.6},ops_per_sec={:.2}",
        sec, ops
    );
}
