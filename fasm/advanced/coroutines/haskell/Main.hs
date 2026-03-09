{-# LANGUAGE ForeignFunctionInterface #-}

import Control.Monad (forM_)
import Data.Int (Int64)
import Data.Word (Word8)
import Data.Time.Clock.POSIX (getPOSIXTime)
import Foreign
import System.Environment (getArgs)


data Generator = Generator
  { gFresh :: Word8
  , gDead :: Word8
  , gRsp :: Ptr ()
  , gStackBase :: Ptr ()
  , gFunc :: Ptr ()
  }

instance Storable Generator where
  sizeOf _ = 32
  alignment _ = 8

  peek p = do
    fresh <- peekByteOff p 0
    dead <- peekByteOff p 1
    rsp <- peekByteOff p 8
    stackBase <- peekByteOff p 16
    func <- peekByteOff p 24
    pure $ Generator fresh dead rsp stackBase func

  poke p g = do
    pokeByteOff p 0 (gFresh g)
    pokeByteOff p 1 (gDead g)
    mapM_ (\o -> pokeByteOff p o (0 :: Word8)) [2 .. 7]
    pokeByteOff p 8 (gRsp g)
    pokeByteOff p 16 (gStackBase g)
    pokeByteOff p 24 (gFunc g)

foreign import ccall "python_generator_init"
  cInit :: IO ()

foreign import ccall "python_generator_next"
  cNext :: Ptr Generator -> Ptr () -> IO (Ptr ())

foreign import ccall "bench_coroutine_func"
  cBenchCoroutineFunc :: Ptr ()

nowNs :: IO Int64
nowNs = do
  t <- getPOSIXTime
  pure $ floor (t * 1000000000)

main :: IO ()
main = do
  args <- getArgs
  let iters = case args of
        (x:_) -> read x
        _ -> 200000 :: Int

  cInit

  let stackCapacity = 1024 * 4096
  stackMem <- mallocBytes stackCapacity

  t0 <- nowNs

  alloca $ \gPtr -> do
    poke gPtr (Generator 1 0 nullPtr stackMem cBenchCoroutineFunc)
    r1 <- cNext gPtr nullPtr
    r2 <- cNext gPtr (intPtrToPtr 42)
    r3 <- cNext gPtr (intPtrToPtr 84)
    if ptrToIntPtr r1 /= 1 || ptrToIntPtr r2 /= 2 || r3 /= nullPtr
      then fail "sequence mismatch"
      else pure ()

  t1 <- nowNs
  let sec = fromIntegral (t1 - t0) / 1e9 :: Double
      ops = 1.0 / sec

  putStrLn $ "lang=haskell,iters=1,total_sec=" ++ show sec ++ ",ops_per_sec=" ++ show ops
