mutable struct Generator
    fresh::UInt8
    dead::UInt8
    pad1::UInt8
    pad2::UInt8
    pad3::UInt8
    pad4::UInt8
    pad5::UInt8
    pad6::UInt8
    rsp::Ptr{Cvoid}
    stack_base::Ptr{Cvoid}
    func::Ptr{Cvoid}
end

const lib = joinpath(@__DIR__, "..", "libcoroutines.so")

ccall((:python_generator_init, lib), Cvoid, ())

stack_capacity = 1024 * 4096
stack_mem = Base.Libc.malloc(stack_capacity)
bench_func = cglobal((:bench_coroutine_func, lib), Cvoid)

g = Generator(0x01, 0x00, 0, 0, 0, 0, 0, 0, C_NULL, stack_mem, bench_func)

start = time_ns()
r1 = ccall((:python_generator_next, lib), Ptr{Cvoid}, (Ptr{Generator}, Ptr{Cvoid}), Ref(g), C_NULL)
r2 = ccall((:python_generator_next, lib), Ptr{Cvoid}, (Ptr{Generator}, Ptr{Cvoid}), Ref(g), Ptr{Cvoid}(42))
r3 = ccall((:python_generator_next, lib), Ptr{Cvoid}, (Ptr{Generator}, Ptr{Cvoid}), Ref(g), Ptr{Cvoid}(84))
sec = (time_ns() - start) / 1e9

if r1 == C_NULL || r2 == C_NULL || r3 != C_NULL
    error("unexpected sequence: r1=$r1 r2=$r2 r3=$r3")
end

ops = 1.0 / sec
println("lang=julia,iters=1,total_sec=$(round(sec, digits=6)),ops_per_sec=$(round(ops, digits=2))")
