#source ~/.bashrc
#kmake-image-run generate_boot_bins.sh efi --ramdisk /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/ramdisk.gz  --systemd-boot /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/github/artifacts/systemd/usr/lib/systemd/boot/efi/systemd-bootaa64.efi  --stub /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/github/artifacts/systemd/usr/lib/systemd/boot/efi/linuxaa64.efi.stub --linux /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux-next/arch/arm64/boot/Image --cmdline "console=ttyMSM0,115200n8 nokaslr maxcpus=8 loglevels=8   earlycon=qcom_geni,0x880000 androidboot.hardware=qcom androidboot.console=ttyMSM0 androidboot.memcg=1 lpm_levels.sleep_disabled=1 video=vfb:640x400,bpp=32,memsize=3072000 msm_rtb.filter=0x237 service_locator.enable=1 androidboot.usbcontroller=a60000   qcom_scm.download_mode=1" --output /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/images	
		
#kmake-image-run generate_boot_bins.sh dtb --input /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux-next/arch/arm64/boot/dts/qcom/qcs615-ride.dtb --output /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/images

#github
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/github/qli-mainline/kernel/arch/arm64/boot/Image ./linux_image/
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/github/qli-mainline/kernel/arch/arm64/boot/dts/qcom/qcs615-ride.dtb ./linux_image/ 
#echo "copy github done"

#linux-next
#qcs615
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux-next/arch/arm64/boot/Image ./linux_image/
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux-next/arch/arm64/boot/dts/qcom/qcs615-ride.dtb ./linux_image/ 
#echo "copy linux-next done"

#qcs615-evk
cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux-next/arch/arm64/boot/Image ./linux_image/
cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux-next/arch/arm64/boot/dts/qcom/talos-evk.dtb ./linux_image/qcs615-ride.dtb 
echo "copy linux-next talos-evk done"

#linux LKP adv
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/LKP_advanced/kernel_platform/kernel/arch/arm64/boot/Image ./linux_image/
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/LKP_advanced/kernel_platform/kernel/arch/arm64/boot/dts/qcom/qcs615-ride.dtb ./linux_image/ 
#echo "copy linux LKP adv done"

#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/kobj/arch/arm64/boot/Image ./linux_image/
#cp /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/kobj/arch/arm64/boot/dts/qcom/qcs615-ride.dtb ./linux_image/ 

#alias kmake-image-run='docker run -it --rm --workdir="$PWD" -v "$(dirname $PWD)":"$(dirname $PWD)" kmake-image'
#alias kmake='kmake-image-run make'

generate_boot_bins.sh efi --ramdisk /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/ramdisk.gz  --systemd-boot /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/efi_dir/systemd-bootaa64.efi  --stub /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/efi_dir/linuxaa64.efi.stub --linux /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux_image/Image --cmdline "console=ttyMSM0,115200n8 nokaslr maxcpus=8 loglevels=8   earlycon=qcom_geni,0x880000 androidboot.hardware=qcom androidboot.console=ttyMSM0 androidboot.memcg=1 lpm_levels.sleep_disabled=1 video=vfb:640x400,bpp=32,memsize=3072000 msm_rtb.filter=0x237 service_locator.enable=1 androidboot.usbcontroller=a60000  qcom_scm.download_mode=1  reboot=panic_warm" --output /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/images
generate_boot_bins.sh dtb --input /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/linux_image/talos-evk.dtb --output /local/mnt/workspace/yyj/develop_linux/git-repository/Talos_repository/upstream_linux-next/linux-sheepdog/images

		
		
