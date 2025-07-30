import os


'''
    Generate test, small and large workload for compression test.

    :param data_dir: directory where benchmark data is placed
    :param size: workload size
    :param input_buckets: input storage containers for this benchmark
    :param output_buckets:
    :param upload_func: upload function taking three params(bucket_idx, key, filepath)
'''
def generate_input(data_dir):

    # upload model
    model_name = 'resnet50-0676ba61.pth'
    #upload_func(0, model_name, os.path.join(data_dir, 'model', model_name))

    input_images = []
    resnet_path = os.path.join(data_dir, 'fake-resnet')
    with open(os.path.join(resnet_path, 'val_map.txt'), 'r') as f:
        for line in f:
            img, img_class = line.split()
            input_images.append((img, img_class))
            #upload_func(1, img, os.path.join(resnet_path, img))

    #input_config = {'object': {}, 'bucket': {}}
    #input_config['object']['model'] = model_name
    #input_config['object']['input'] = input_images[0][0]
    #input_config['bucket']['bucket'] = benchmarks_bucket
    #input_config['bucket']['input'] = input_paths[1]
    #input_config['bucket']['model'] = input_paths[0]
    print(input_images[0][0])
    #return input_config
generate_input("/scratch/patrick/wallet-current/Benchmarks/SeBS/benchmarks-data/400.inference/411.image-recognition/")
