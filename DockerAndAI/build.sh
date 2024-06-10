#!/bin/sh

# current date in the format: 2024-05-23.09H10
TAG_DATE=$(date +%Y-%m-%d.%HH%M)

# detect if an external image registry is configured
if [ "z${IMGREGISTRY}z" = "zz" ]; then
    echo "An image registry is required for Kubernetes. Please set env variable IMGREGISTRY"
    REGISTRY_TAG=""
    PUBLISH=0
else
    REGISTRY_TAG="-t ${IMGREGISTRY}/dockerblog:${TAG_DATE}"
    PUBLISH=1
fi


docker build -t dockerblog:$TAG_DATE \
             -t dockerblog:latest \
             $REGISTRY_TAG \
    --label "builton=$(hostname)" \
    --label "builtby=$(whoami)" \
    . >build.log 2>&1

BUILD_CODE=$?

#check the return status of the build command
if [ $BUILD_CODE -eq 0 ] ; then
    # print image size
    IMG_SIZE=$(docker image  ls dockerblog:$TAG_DATE --format json | jq -r '.Size')
    echo "Image dockerblog:${TAG_DATE} size is ${IMG_SIZE}" 

    if [ $PUBLISH -eq 1 ] ; then
        echo publishing image to $IMGREGISTRY
        docker push ${IMGREGISTRY}/dockerblog:${TAG_DATE} 
        echo 
        echo "To update your running deployment, execute"
        echo kubectl -n dockerblog set image deployment/dummydep my-supper-app=${IMGREGISTRY}/dockerblog:${TAG_DATE}
    fi
else
    echo !! Image build failed !!
    echo " - - - - build.log - - - "
    # print the content of the log file with a tab prefix to make it look like indentation
    awk '{ print "\t" $0 }' build.log
    echo " - - - - - - - - - - - - - "
fi
