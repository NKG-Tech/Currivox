/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  // Optionnel: si tu utilises des images distantes
  // images: {
  //   remotePatterns: [
  //     { protocol: 'https', hostname: '**' }
  //   ]
  // }
};
export default nextConfig;
