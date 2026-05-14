const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_LEADGEN_API_URL: process.env.NEXT_PUBLIC_LEADGEN_API_URL,
  },
}
export default nextConfig
