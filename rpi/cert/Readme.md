In this folder you need to store the TLS certificates which you get from AWS IoT while "connect a thing" over the Management console of AWS.
Structure your files as follows

    ./cert
        ./{thing_name}
            ./certificate.pem.crt
            ./private.pem.key

where *{thing_name}* is the name of your thing as registered in AWS IoT.